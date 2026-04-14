"""Tests for the Dream class — two-phase memory consolidation via AgentRunner."""

import pytest

from unittest.mock import AsyncMock, MagicMock

from nanobot.agent.memory import Dream, MemoryStore
from nanobot.agent.runner import AgentRunResult
from nanobot.agent.skills import BUILTIN_SKILLS_DIR


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(tmp_path)
    s.write_soul("# Soul\n- Helpful")
    s.write_user("# User\n- Developer")
    s.write_memory("# Memory\n- Project X active")
    return s


@pytest.fixture
def mock_provider():
    p = MagicMock()
    p.chat_with_retry = AsyncMock()
    return p


@pytest.fixture
def mock_runner():
    return MagicMock()


@pytest.fixture
def dream(store, mock_provider, mock_runner):
    d = Dream(store=store, provider=mock_provider, model="test-model", max_batch_size=5)
    d._runner = mock_runner
    return d


def _make_run_result(
    stop_reason="completed",
    final_content=None,
    tool_events=None,
    usage=None,
):
    return AgentRunResult(
        final_content=final_content or stop_reason,
        stop_reason=stop_reason,
        messages=[],
        tools_used=[],
        usage={},
        tool_events=tool_events or [],
    )


class TestDreamRun:
    async def test_noop_when_no_unprocessed_history(self, dream, mock_provider, mock_runner, store):
        """Dream should not call LLM when there's nothing to process."""
        result = await dream.run()
        assert result is False
        mock_provider.chat_with_retry.assert_not_called()
        mock_runner.run.assert_not_called()

    async def test_calls_runner_for_unprocessed_entries(
        self, dream, mock_provider, mock_runner, store
    ):
        """Dream should call AgentRunner when there are unprocessed history entries."""
        store.append_history("User prefers dark mode")
        mock_provider.chat_with_retry.return_value = MagicMock(content="New fact")
        mock_runner.run = AsyncMock(
            return_value=_make_run_result(
                tool_events=[{"name": "edit_file", "status": "ok", "detail": "memory/MEMORY.md"}],
            )
        )
        result = await dream.run()
        assert result is True
        mock_runner.run.assert_called_once()
        spec = mock_runner.run.call_args[0][0]
        assert spec.max_iterations == 10
        assert spec.fail_on_tool_error is False

    async def test_advances_dream_cursor(self, dream, mock_provider, mock_runner, store):
        """Dream should advance the cursor after processing."""
        store.append_history("event 1")
        store.append_history("event 2")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Nothing new")
        mock_runner.run = AsyncMock(return_value=_make_run_result())
        await dream.run()
        assert store.get_last_dream_cursor() == 2

    async def test_compacts_processed_history(self, dream, mock_provider, mock_runner, store):
        """Dream should compact history after processing."""
        store.append_history("event 1")
        store.append_history("event 2")
        store.append_history("event 3")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Nothing new")
        mock_runner.run = AsyncMock(return_value=_make_run_result())
        await dream.run()
        # After Dream, cursor is advanced and 3, compact keeps last max_history_entries
        entries = store.read_unprocessed_history(since_cursor=0)
        assert all(e["cursor"] > 0 for e in entries)

    async def test_skill_phase_uses_builtin_skill_creator_path(
        self, dream, mock_provider, mock_runner, store
    ):
        """Dream should point skill creation guidance at the builtin skill-creator template."""
        store.append_history("Repeated workflow one")
        store.append_history("Repeated workflow two")
        mock_provider.chat_with_retry.return_value = MagicMock(
            content="[SKILL] test-skill: test description"
        )
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        await dream.run()

        spec = mock_runner.run.call_args[0][0]
        system_prompt = spec.initial_messages[0]["content"]
        expected = str(BUILTIN_SKILLS_DIR / "skill-creator" / "SKILL.md")
        assert expected in system_prompt

    async def test_skill_write_tool_accepts_workspace_relative_skill_path(self, dream, store):
        """Dream skill creation should allow skills/<name>/SKILL.md relative to workspace root."""
        write_tool = dream._tools.get("write_file")
        assert write_tool is not None

        result = await write_tool.execute(
            path="skills/test-skill/SKILL.md",
            content="---\nname: test-skill\ndescription: Test\n---\n",
        )

        assert "Successfully wrote" in result
        assert (store.workspace / "skills" / "test-skill" / "SKILL.md").exists()


class TestDreamHook:
    """Tests for the hook script feature after Dream completion."""

    async def test_no_hook_when_not_configured(self, store, mock_provider, mock_runner):
        """Dream should not invoke hook when after_hook_script is not configured."""
        dream = Dream(store=store, provider=mock_provider, model="test-model")
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        await dream.run()
        # No exception should be raised; hook is simply not invoked

    async def test_hook_invoked_when_configured_and_script_exists(
        self, store, mock_provider, mock_runner, tmp_path
    ):
        """Dream should invoke hook script when configured and script exists."""
        marker = tmp_path / "hook_executed.txt"
        after_hook_script = tmp_path / "hook.py"
        after_hook_script.write_text(
            f"""
import pathlib
def run(ctx):
    pathlib.Path("{marker}").write_text("ok")
""",
            encoding="utf-8",
        )

        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(after_hook_script),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        await dream.run()
        # Wait for thread pool to complete
        import asyncio

        await asyncio.sleep(0.1)

        # Hook should have created the marker file
        assert marker.exists()
        assert marker.read_text() == "ok"

    async def test_hook_missing_script_no_error(self, store, mock_provider, mock_runner, tmp_path):
        """Dream should complete without error when configured script does not exist."""
        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(tmp_path / "nonexistent.py"),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        # Should complete without raising any error
        result = await dream.run()
        assert result is True

    async def test_hook_missing_run_function_no_crash(
        self, store, mock_provider, mock_runner, tmp_path
    ):
        """Dream should not crash when hook script has no run function."""
        after_hook_script = tmp_path / "hook_no_run.py"
        after_hook_script.write_text(
            """
def other_function(ctx):
    pass
""",
            encoding="utf-8",
        )

        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(after_hook_script),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        # Should complete without raising
        result = await dream.run()
        assert result is True

    async def test_hook_exception_does_not_crash_dream(
        self, store, mock_provider, mock_runner, tmp_path
    ):
        """Dream should catch hook exceptions and continue without crashing."""
        after_hook_script = tmp_path / "hook_crash.py"
        after_hook_script.write_text(
            """
def run(ctx):
    raise ValueError("Hook error!")
""",
            encoding="utf-8",
        )

        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(after_hook_script),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        # Should not raise; exception is caught and logged
        result = await dream.run()
        assert result is True  # Dream still completes successfully

    async def test_hook_context_contains_expected_keys(
        self, store, mock_provider, mock_runner, tmp_path
    ):
        """Dream should pass correct context to hook script."""
        ctx_file = tmp_path / "ctx.json"
        after_hook_script = tmp_path / "hook_capture.py"
        after_hook_script.write_text(
            f"""
import json
import pathlib
def run(ctx):
    pathlib.Path("{ctx_file}").write_text(
        json.dumps({{k: str(v)[:100] for k, v in ctx.items()}})
    )
""",
            encoding="utf-8",
        )

        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(after_hook_script),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(
            return_value=_make_run_result(
                tool_events=[{"name": "edit_file", "status": "ok", "detail": "test"}]
            )
        )

        await dream.run()
        # Wait for thread pool to complete
        import asyncio

        await asyncio.sleep(0.1)

        import json

        assert ctx_file.exists()
        captured_ctx = json.loads(ctx_file.read_text())
        assert "changelog" in captured_ctx
        assert "cursor" in captured_ctx
        assert "batch" in captured_ctx
        assert "result" in captured_ctx

    async def test_hook_handles_batch_cursor_safely(
        self, store, mock_provider, mock_runner, tmp_path
    ):
        """Dream should pass cursor from batch to hook context."""
        cursor_file = tmp_path / "cursor.txt"
        after_hook_script = tmp_path / "hook_cursor.py"
        after_hook_script.write_text(
            f"""
import pathlib
def run(ctx):
    pathlib.Path("{cursor_file}").write_text(str(ctx.get("cursor")))
""",
            encoding="utf-8",
        )

        dream = Dream(
            store=store,
            provider=mock_provider,
            model="test-model",
            after_hook_script=str(after_hook_script),
        )
        dream._runner = mock_runner

        store.append_history("event 1")
        mock_provider.chat_with_retry.return_value = MagicMock(content="Done")
        mock_runner.run = AsyncMock(return_value=_make_run_result())

        await dream.run()
        # Wait for thread pool to complete
        import asyncio

        await asyncio.sleep(0.1)

        assert cursor_file.exists()
        # Cursor should be a number (from batch[-1].get("cursor"))
        assert cursor_file.read_text() == "1"
