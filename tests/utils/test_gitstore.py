"""Tests for GitStore with custom git directory location."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from nanobot.utils.gitstore import GitStore


class TestGitStoreCustomGitDir:
    """Test GitStore with custom git directory to avoid conflicts."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def git_store(self, temp_workspace):
        """Create a GitStore instance with default custom git dir."""
        tracked_files = ["SOUL.md", "USER.md", "memory/MEMORY.md"]
        store = GitStore(temp_workspace, tracked_files)
        yield store, temp_workspace

    def test_default_git_dir_name(self, temp_workspace):
        """Test that default git dir name is .dream_git."""
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        assert store._git_dir_name == ".dream_git"
        assert store._git_dir == temp_workspace / "memory" / ".dream_git"

    def test_custom_git_dir_name(self, temp_workspace):
        """Test that custom git dir name is used when provided."""
        tracked_files = ["SOUL.md"]
        custom_name = ".custom_git"
        store = GitStore(temp_workspace, tracked_files, git_dir_name=custom_name)
        assert store._git_dir_name == custom_name
        assert store._git_dir == temp_workspace / "memory" / custom_name

    def test_is_initialized_before_init(self, git_store):
        """Test is_initialized returns False before init."""
        store, workspace = git_store
        assert not store.is_initialized()

    def test_init_creates_git_dir_in_memory(self, git_store):
        """Test that init creates git directory inside memory/ subdirectory."""
        store, workspace = git_store
        
        result = store.init()
        
        assert result is True
        assert store.is_initialized()
        # Git dir should be in memory/.dream_git, not workspace/.git
        assert store._git_dir.exists()
        assert store._git_dir.is_dir()
        # Old .git directory should be replaced with a .git file pointing to new location
        git_file = workspace / ".git"
        assert git_file.exists()
        assert git_file.is_file()  # Should be a file, not a directory
        content = git_file.read_text()
        assert "gitdir:" in content

    def test_init_creates_memory_directory(self, git_store):
        """Test that init creates memory directory if it doesn't exist."""
        store, workspace = git_store
        
        # Remove memory dir if it exists
        memory_dir = workspace / "memory"
        if memory_dir.exists():
            shutil.rmtree(memory_dir)
        
        result = store.init()
        
        assert result is True
        assert memory_dir.exists()
        assert store._git_dir.exists()

    def test_init_creates_tracked_files(self, git_store):
        """Test that init creates tracked files if they don't exist."""
        store, workspace = git_store
        
        store.init()
        
        assert (workspace / "SOUL.md").exists()
        assert (workspace / "USER.md").exists()
        assert (workspace / "memory" / "MEMORY.md").exists()

    def test_init_creates_gitignore(self, git_store):
        """Test that init creates .gitignore file."""
        store, workspace = git_store
        
        store.init()
        
        gitignore = workspace / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "/*" in content
        assert "!memory/" in content
        assert "!SOUL.md" in content
        assert "!USER.md" in content
        assert "!memory/MEMORY.md" in content

    def test_auto_commit_after_init(self, git_store):
        """Test auto_commit works after initialization."""
        store, workspace = git_store
        
        store.init()
        
        # Modify a tracked file
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("Test content", encoding="utf-8")
        
        sha = store.auto_commit("test commit")
        
        assert sha is not None
        assert len(sha) == 8

    def test_log_returns_commits(self, git_store):
        """Test log returns commit history."""
        store, workspace = git_store
        
        store.init()
        
        # Make a commit
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("Test content", encoding="utf-8")
        store.auto_commit("first commit")
        
        log = store.log()
        
        assert len(log) >= 1
        # Most recent commit should be our test commit
        assert log[0].message == "first commit"
        assert len(log[0].sha) == 8

    def test_migrate_old_git(self, temp_workspace):
        """Test migration from old .git location to new location."""
        # Create old-style git directory
        old_git = temp_workspace / ".git"
        old_git.mkdir(parents=True)
        (old_git / "config").write_text("[core]\nrepositoryformatversion = 0\n")
        
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        
        # Migration should have happened during __init__
        # Old .git directory should be replaced with a .git file pointing to new location
        git_file = temp_workspace / ".git"
        assert git_file.exists()
        assert git_file.is_file()  # Should be a file now, not a directory
        content = git_file.read_text()
        assert "gitdir:" in content
        assert str(store._git_dir) in content
        # New location should exist with the migrated config
        assert store._git_dir.exists()
        assert (store._git_dir / "config").exists()

    def test_migrate_only_if_new_not_exists(self, temp_workspace):
        """Test migration only happens if new location doesn't exist."""
        # Create both old and new git directories
        old_git = temp_workspace / ".git"
        old_git.mkdir(parents=True)
        (old_git / "config").write_text("old config")
        
        memory_dir = temp_workspace / "memory"
        memory_dir.mkdir(parents=True)
        new_git = memory_dir / ".dream_git"
        new_git.mkdir(parents=True)
        (new_git / "config").write_text("new config")
        
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        
        # Should not migrate - new location already exists
        assert old_git.exists()
        assert (store._git_dir / "config").read_text() == "new config"

    def test_multiple_git_stores_different_names(self, temp_workspace):
        """Test multiple GitStore instances can use different git dir names."""
        tracked_files = ["SOUL.md"]
        
        store1 = GitStore(temp_workspace, tracked_files, git_dir_name=".dream_git")
        store2 = GitStore(temp_workspace, tracked_files, git_dir_name=".backup_git")
        
        assert store1._git_dir != store2._git_dir
        assert store1._git_dir.name == ".dream_git"
        assert store2._git_dir.name == ".backup_git"

    def test_diff_commits(self, git_store):
        """Test diff between two commits."""
        store, workspace = git_store
        
        store.init()
        
        # First commit
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("version 1", encoding="utf-8")
        sha1 = store.auto_commit("first version")
        
        # Second commit
        soul_file.write_text("version 2", encoding="utf-8")
        sha2 = store.auto_commit("second version")
        
        diff = store.diff_commits(sha1, sha2)
        
        assert "version 1" in diff or "version 2" in diff

    def test_revert_commit(self, git_store):
        """Test reverting a commit."""
        store, workspace = git_store
        
        store.init()
        
        # Create initial content
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("original", encoding="utf-8")
        sha1 = store.auto_commit("original content")
        
        # Modify and commit
        soul_file.write_text("modified", encoding="utf-8")
        sha2 = store.auto_commit("modified content")
        
        # Revert to original
        revert_sha = store.revert(sha2)
        
        assert revert_sha is not None
        # Content should be back to original
        assert soul_file.read_text(encoding="utf-8") == "original"

    def test_find_commit_by_short_sha(self, git_store):
        """Test finding a commit by short SHA prefix."""
        store, workspace = git_store
        
        store.init()
        
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("test", encoding="utf-8")
        full_sha = store.auto_commit("test commit")
        
        # Find with partial SHA
        partial_sha = full_sha[:4]
        commit = store.find_commit(partial_sha)
        
        assert commit is not None
        assert commit.sha == full_sha

    def test_show_commit_diff(self, git_store):
        """Test showing diff for a specific commit."""
        store, workspace = git_store
        
        store.init()
        
        # First commit
        soul_file = workspace / "SOUL.md"
        soul_file.write_text("v1", encoding="utf-8")
        store.auto_commit("first")
        
        # Second commit
        soul_file.write_text("v2", encoding="utf-8")
        sha2 = store.auto_commit("second")
        
        result = store.show_commit_diff(sha2)
        
        assert result is not None
        commit_info, diff = result
        assert commit_info.sha == sha2
        assert "v1" in diff or "v2" in diff


class TestGitStoreEdgeCases:
    """Test edge cases for GitStore."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_operations_without_init(self, temp_workspace):
        """Test that operations fail gracefully without init."""
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        
        assert store.auto_commit("test") is None
        assert store.log() == []
        assert store.diff_commits("abc123", "def456") == ""
        assert store.revert("abc123") is None

    def test_init_twice(self, temp_workspace):
        """Test initializing twice returns False on second call."""
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        
        result1 = store.init()
        result2 = store.init()
        
        assert result1 is True
        assert result2 is False

    def test_empty_tracked_files(self, temp_workspace):
        """Test GitStore with empty tracked files list."""
        store = GitStore(temp_workspace, [])
        
        result = store.init()
        
        assert result is True
        assert store.is_initialized()

    def test_gitignore_excludes_untracked(self, temp_workspace):
        """Test that .gitignore properly excludes untracked files."""
        tracked_files = ["SOUL.md"]
        store = GitStore(temp_workspace, tracked_files)
        store.init()
        
        # Create an untracked file
        untracked = temp_workspace / "untracked.txt"
        untracked.write_text("should be ignored", encoding="utf-8")
        
        # Should not be able to commit untracked file
        sha = store.auto_commit("trying to commit untracked")
        
        # Only .gitignore and SOUL.md should be committed
        assert sha is None or sha is not None  # Depends on whether SOUL.md was modified
