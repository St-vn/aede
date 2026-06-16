from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


# ── T1 — SoulDef + VoiceDef dataclasses ──
def test_souldef_default_construction():
    from aede.instructions import SoulDef, VoiceDef
    s = SoulDef()
    assert s.name is None
    assert s.phonetic is None
    assert s.wake_word is None
    assert s.wake_word_phonetic is None
    assert s.persona == ""
    assert s.aliases == []
    assert s.source_files == []
    assert isinstance(s.voice, VoiceDef)
    assert s.voice.engine is None
    assert s.voice.voice_id is None
    assert s.voice.rate == 1.0
    assert s.voice.pitch == 1.0


def test_souldef_manual_construction_full():
    from aede.instructions import SoulDef, VoiceDef
    s = SoulDef(
        name="Jarvis",
        phonetic="/ˈdʒɑːvɪs/",
        wake_word="hey jarvis",
        wake_word_phonetic="/heɪ ˈdʒɑːvɪs/",
        persona="British butler. Concise and dry.",
        voice=VoiceDef(engine="piper", voice_id="en-GB-Ryan", rate=1.0, pitch=1.0),
        aliases=["jarvis", "j"],
        source_files=["/home/x/.aede/SOUL.md"],
    )
    assert s.name == "Jarvis"
    assert s.wake_word == "hey jarvis"
    assert s.voice.engine == "piper"
    assert s.voice.voice_id == "en-GB-Ryan"
    assert s.aliases == ["jarvis", "j"]
    assert s.source_files == ["/home/x/.aede/SOUL.md"]


# ── T2 — _parse_frontmatter ──

@pytest.fixture
def console():
    c = MagicMock()
    c.print = MagicMock()
    return c


def test_parse_frontmatter_valid_yaml_block():
    from aede.instructions import _parse_frontmatter
    text = "---\nname: Jarvis\nwake_word: hey jarvis\n---\nBritish butler.\n"
    frontmatter, body = _parse_frontmatter(text, console=None)
    assert frontmatter == {"name": "Jarvis", "wake_word": "hey jarvis"}
    assert body == "British butler.\n"


def test_parse_frontmatter_no_block_returns_empty_and_full_body():
    from aede.instructions import _parse_frontmatter
    text = "British butler. Concise and dry.\n"
    frontmatter, body = _parse_frontmatter(text, console=None)
    assert frontmatter == {}
    assert body == "British butler. Concise and dry.\n"


def test_parse_frontmatter_empty_block():
    from aede.instructions import _parse_frontmatter
    text = "---\n---\nPersona only.\n"
    frontmatter, body = _parse_frontmatter(text, console=None)
    assert frontmatter == {}
    assert body == "Persona only.\n"


def test_parse_frontmatter_unclosed_delimiter_treats_as_body():
    from aede.instructions import _parse_frontmatter
    text = "---\nname: half-baked\nstill going..."
    frontmatter, body = _parse_frontmatter(text, console=None)
    assert frontmatter == {}
    assert body == text


def test_parse_frontmatter_malformed_yaml_warns_and_returns_body(console):
    from aede.instructions import _parse_frontmatter
    text = "---\nname: [unclosed bracket\n---\nBody text.\n"
    frontmatter, body = _parse_frontmatter(text, console=console)
    assert frontmatter == {}
    assert body == "Body text.\n"
    console.print.assert_called_once()
    msg = console.print.call_args[0][0]
    assert "SOUL.md" in msg and "frontmatter" in msg and "ignoring" in msg


def test_parse_frontmatter_non_dict_yaml_root_warns(console):
    from aede.instructions import _parse_frontmatter
    text = "---\n- just a list\n---\nBody.\n"
    frontmatter, body = _parse_frontmatter(text, console=console)
    assert frontmatter == {}
    assert body == "Body.\n"
    console.print.assert_called_once()


# ── T3 — load_soul_def (3-layer merge) ──

def test_load_soul_def_global_only(tmp_home):
    from aede.instructions import load_soul_def
    (tmp_home / "SOUL.md").write_text(
        "---\nname: Alice\nwake_word: al\n---\nGlobal voice.\n", encoding="utf-8"
    )
    s = load_soul_def(home=tmp_home, project_dir=tmp_home / "no-project")
    assert s.name == "Alice"
    assert s.wake_word == "al"
    assert s.persona == "Global voice.\n"
    assert s.source_files == [str(tmp_home / "SOUL.md")]


def test_load_soul_def_project_only(tmp_home, tmp_path):
    from aede.instructions import load_soul_def
    project = tmp_path / "proj"
    project.mkdir()
    (project / "SOUL.md").write_text(
        "---\nname: Bob\n---\nProject voice.\n", encoding="utf-8"
    )
    s = load_soul_def(home=tmp_home, project_dir=project)
    assert s.name == "Bob"
    assert s.persona == "Project voice.\n"
    assert s.source_files == [str(project / "SOUL.md")]


def test_load_soul_def_project_overrides_name_inherits_aliases(tmp_home, tmp_path):
    from aede.instructions import load_soul_def
    (tmp_home / "SOUL.md").write_text(
        "---\nname: Alice\naliases: [a, al]\n---\nGlobal voice.\n", encoding="utf-8"
    )
    project = tmp_path / "proj"
    project.mkdir()
    (project / "SOUL.md").write_text(
        "---\nname: Bob\n---\nProject voice.\n", encoding="utf-8"
    )
    s = load_soul_def(home=tmp_home, project_dir=project)
    assert s.name == "Bob"
    assert s.aliases == ["a", "al"]
    assert s.persona == "Project voice.\n"


def test_load_soul_def_missing_both_files_returns_empty(tmp_home, tmp_path):
    from aede.instructions import load_soul_def
    project = tmp_path / "proj"
    project.mkdir()
    s = load_soul_def(home=tmp_home, project_dir=project)
    assert s.name is None
    assert s.wake_word is None
    assert s.persona == ""
    assert s.aliases == []
    assert s.voice.engine is None
    assert s.source_files == []


def test_load_soul_def_coerces_voice_rate_and_pitch_to_float(tmp_home):
    from aede.instructions import load_soul_def
    (tmp_home / "SOUL.md").write_text(
        "---\nvoice:\n  engine: piper\n  voice_id: en-GB-Ryan\n  rate: 1\n  pitch: 1\n---\n",
        encoding="utf-8",
    )
    s = load_soul_def(home=tmp_home, project_dir=tmp_home / "no-project")
    assert s.voice.engine == "piper"
    assert s.voice.voice_id == "en-GB-Ryan"
    assert s.voice.rate == 1.0 and isinstance(s.voice.rate, float)
    assert s.voice.pitch == 1.0 and isinstance(s.voice.pitch, float)


def test_load_soul_def_plain_markdown_backward_compatible(tmp_home, tmp_path):
    from aede.instructions import load_soul_def
    (tmp_home / "SOUL.md").write_text("British butler. Concise and dry.\n", encoding="utf-8")
    s = load_soul_def(home=tmp_home, project_dir=tmp_path / "no-project")
    assert s.name is None
    assert s.persona == "British butler. Concise and dry.\n"
    from aede.instructions import build_instructions_suffix
    suffix = build_instructions_suffix(home=tmp_home, project_dir=tmp_path / "no-project")
    assert "## Identity" in suffix
    assert "British butler" in suffix


# ── T4 — cfg.soul exposure ──

def test_aedeconfig_has_soul_attr(tmp_home):
    from aede.config import AedeConfig
    from aede.instructions import SoulDef
    cfg = AedeConfig({}, home=tmp_home)
    assert isinstance(cfg.soul, SoulDef)


def test_aedeconfig_soul_reflects_soul_md(tmp_home):
    from aede.config import AedeConfig
    (tmp_home / "SOUL.md").write_text(
        "---\nname: Jarvis\nwake_word: hey jarvis\n---\nButler.\n", encoding="utf-8"
    )
    cfg = AedeConfig({}, home=tmp_home)
    assert cfg.soul.name == "Jarvis"
    assert cfg.soul.wake_word == "hey jarvis"
    assert cfg.soul.persona == "Butler.\n"


def test_load_config_persists_project_dir(tmp_home, tmp_path):
    from aede.config import load_config
    project = tmp_path / "proj"
    project.mkdir()
    (project / "SOUL.md").write_text(
        "---\nname: ProjectBot\n---\nProject voice.\n", encoding="utf-8"
    )
    cfg = load_config(home=tmp_home, project_dir=project)
    assert cfg.project_dir == project
    assert cfg.soul.name == "ProjectBot"
    assert cfg.soul.persona == "Project voice.\n"


# ── T6 — SoulTab backend endpoints ──

def test_get_soul_endpoint_returns_souldef(tmp_home, tmp_path):
    from aede.server import app
    from fastapi.testclient import TestClient
    (tmp_home / "SOUL.md").write_text(
        "---\nname: Jarvis\nwake_word: hey jarvis\n---\nButler.\n", encoding="utf-8"
    )
    client = TestClient(app)
    with patch("aede.server.get_config_for_request") as mock_cfg:
        from aede.config import AedeConfig
        mock_cfg.return_value = AedeConfig({}, home=tmp_home, project_dir=tmp_path / "no-project")
        resp = client.get("/api/soul")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Jarvis"
    assert data["wake_word"] == "hey jarvis"
    assert data["persona"] == "Butler.\n"


def test_patch_soul_endpoint_writes_to_project_dir(tmp_home, tmp_path):
    from aede.server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    with patch("aede.server.get_config_for_request") as mock_cfg:
        from aede.config import AedeConfig
        cfg = AedeConfig({}, home=tmp_home, project_dir=tmp_path / "proj")
        mock_cfg.return_value = cfg
        resp = client.patch("/api/soul", json={"name": "TestBot", "wake_word": "hey test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestBot"
    path = tmp_path / "proj" / "SOUL.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "name: TestBot" in text


def test_patch_soul_endpoint_merges_existing_frontmatter(tmp_home, tmp_path):
    from aede.server import app
    from fastapi.testclient import TestClient
    project = tmp_path / "proj"
    project.mkdir()
    (project / "SOUL.md").write_text(
        "---\nname: OldBot\nwake_word: hey old\n---\nExisting persona.\n", encoding="utf-8"
    )
    client = TestClient(app)
    with patch("aede.server.get_config_for_request") as mock_cfg:
        from aede.config import AedeConfig
        cfg = AedeConfig({}, home=tmp_home, project_dir=project)
        mock_cfg.return_value = cfg
        resp = client.patch("/api/soul", json={"name": "NewBot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "NewBot"
    text = (project / "SOUL.md").read_text(encoding="utf-8")
    assert "name: NewBot" in text
    assert "wake_word: hey old" in text
    assert "Existing persona." in text


def test_get_soul_endpoint_returns_defaults_when_no_soul_file(tmp_home, tmp_path):
    from aede.server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    with patch("aede.server.get_config_for_request") as mock_cfg:
        from aede.config import AedeConfig
        mock_cfg.return_value = AedeConfig({}, home=tmp_home, project_dir=tmp_path / "no-project")
        resp = client.get("/api/soul")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] is None
    assert data["wake_word"] is None
    assert data["persona"] == ""


# ── T5 — /soul CLI slash command ──

def test_parse_command_recognises_soul():
    from aede.commands import parse_command, COMMANDS
    assert "soul" in COMMANDS
    r = parse_command("/soul")
    assert r is not None and r.name == "soul" and r.args == []


def test_handle_soul_view_prints_effective(tmp_home, tmp_path):
    from aede.commands import handle_soul
    from aede.config import AedeConfig
    (tmp_home / "SOUL.md").write_text(
        "---\nname: Jarvis\nwake_word: hey jarvis\nvoice:\n  engine: piper\n  voice_id: en-GB-Ryan\n  rate: 1.0\n  pitch: 1.0\naliases: [jarvis, j]\n---\nBritish butler. Concise and dry.\n",
        encoding="utf-8",
    )
    cfg = AedeConfig({}, home=tmp_home, project_dir=tmp_path / "no-project")
    console = MagicMock()
    handle_soul(args=[], home=tmp_home, console=console, cfg=cfg,
                project_dir=tmp_path / "no-project")
    out = "\n".join(str(c) for c in console.print.call_args_list)
    assert "Jarvis" in out
    assert "hey jarvis" in out
    assert "piper" in out
    assert "en-GB-Ryan" in out
    assert "jarvis" in out and "j" in out
    assert "British butler" in out
    assert "SOUL.md" in out


def test_handle_soul_global_opens_editor(tmp_home, tmp_path):
    from aede.commands import handle_soul
    from aede.config import AedeConfig
    cfg = AedeConfig({}, home=tmp_home, project_dir=tmp_path / "no-project")
    console = MagicMock()
    with patch("aede.config.edit_config_file", return_value=tmp_home / "SOUL.md") as mock_edit:
        handle_soul(args=["global"], home=tmp_home, console=console, cfg=cfg,
                    project_dir=tmp_path / "no-project")
    mock_edit.assert_called_once()


def test_handle_soul_project_creates_then_opens(tmp_home, tmp_path):
    from aede.commands import handle_soul
    from aede.config import AedeConfig
    project = tmp_path / "proj"
    project.mkdir()
    cfg = AedeConfig({}, home=tmp_home, project_dir=project)
    console = MagicMock()
    assert not (project / "SOUL.md").exists()
    with patch("aede.config.edit_config_file", return_value=project / "SOUL.md") as mock_edit:
        handle_soul(args=["project"], home=tmp_home, console=console, cfg=cfg,
                    project_dir=project)
    mock_edit.assert_called_once()


def test_handle_soul_set_key_writes_to_project_frontmatter(tmp_home, tmp_path):
    from aede.commands import handle_soul
    from aede.config import AedeConfig
    project = tmp_path / "proj"
    project.mkdir()
    cfg = AedeConfig({}, home=tmp_home, project_dir=project)
    console = MagicMock()
    handle_soul(args=["wake_word", "hey jarvis"], home=tmp_home, console=console,
                cfg=cfg, project_dir=project)
    soul_path = project / "SOUL.md"
    assert soul_path.exists()
    text = soul_path.read_text(encoding="utf-8")
    assert "wake_word" in text
    assert "hey jarvis" in text


# ── T7 — AC coverage meta-test + AC-9 SoulTab check ──

def test_soultab_file_exists_and_settings_modal_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    soul_tab = root / "ui" / "components" / "settings" / "tabs" / "SoulTab.tsx"
    assert soul_tab.exists(), f"Missing {soul_tab}"
    modal = root / "ui" / "components" / "settings" / "SettingsModal.tsx"
    text = modal.read_text(encoding="utf-8")
    assert "SoulTab" in text
    # Instructions tab (AGENTS.md / CLAUDE.md editor) is wired too.
    instr_tab = root / "ui" / "components" / "settings" / "tabs" / "InstructionsTab.tsx"
    assert instr_tab.exists(), f"Missing {instr_tab}"
    assert "InstructionsTab" in text
    assert "/api/project-instructions" in instr_tab.read_text(encoding="utf-8")


# ── T6 — PATCH /api/soul scope + persona body ──

def _patch_soul(tmp_home, project, json_body):
    from aede.server import app
    from fastapi.testclient import TestClient
    from aede.config import AedeConfig
    client = TestClient(app)
    with patch("aede.server.get_config_for_request") as mock_cfg:
        mock_cfg.return_value = AedeConfig({}, home=tmp_home, project_dir=project)
        return client.patch("/api/soul", json=json_body)


def test_patch_soul_global_scope_writes_to_home(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    resp = _patch_soul(tmp_home, project, {"name": "GlobalBot", "scope": "global"})
    assert resp.status_code == 200
    # Global scope writes to home, NOT project_dir.
    assert (tmp_home / "SOUL.md").exists()
    assert not (project / "SOUL.md").exists()
    assert "name: GlobalBot" in (tmp_home / "SOUL.md").read_text(encoding="utf-8")


def test_patch_soul_project_scope_writes_to_project(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    resp = _patch_soul(tmp_home, project, {"name": "ProjBot", "scope": "project"})
    assert resp.status_code == 200
    assert (project / "SOUL.md").exists()
    assert not (tmp_home / "SOUL.md").exists()


def test_patch_soul_persona_body_written(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    resp = _patch_soul(tmp_home, project, {
        "name": "BodyBot", "persona": "You are calm and terse.", "scope": "project",
    })
    assert resp.status_code == 200
    assert resp.json()["persona"] == "You are calm and terse."
    text = (project / "SOUL.md").read_text(encoding="utf-8")
    assert "You are calm and terse." in text


def test_patch_soul_aliases_list_roundtrips(tmp_home, tmp_path):
    # The old f-string serializer broke on list values; safe_dump must round-trip.
    project = tmp_path / "proj"
    project.mkdir()
    (project / "SOUL.md").write_text(
        "---\nname: OldBot\naliases:\n- jarvis\n- friday\n---\nbody\n", encoding="utf-8"
    )
    resp = _patch_soul(tmp_home, project, {"name": "NewBot", "scope": "project"})
    assert resp.status_code == 200
    from aede.instructions import _parse_frontmatter
    fm, _ = _parse_frontmatter((project / "SOUL.md").read_text(encoding="utf-8"))
    assert fm["name"] == "NewBot"
    assert fm["aliases"] == ["jarvis", "friday"]


def test_all_p0_8_acs_have_tests():
    from pathlib import Path
    text = Path(__file__).resolve().read_text(encoding="utf-8")
    expected = [
        "test_souldef_manual_construction_full",
        "test_load_soul_def_global_only",
        "test_load_soul_def_plain_markdown_backward_compatible",
        "test_load_soul_def_project_overrides_name_inherits_aliases",
        "test_aedeconfig_has_soul_attr",
        "test_parse_frontmatter_malformed_yaml_warns_and_returns_body",
        "test_load_soul_def_missing_both_files_returns_empty",
        "test_handle_soul_view_prints_effective",
        "test_handle_soul_global_opens_editor",
        "test_handle_soul_project_creates_then_opens",
        "test_soultab_file_exists_and_settings_modal_wired",
    ]
    missing = [s for s in expected if s not in text]
    assert not missing, f"Missing AC tests: {missing}"
