"""Strip unused tau2-bench subpackages so the import chain stays minimal.

Called once by prepare.sh after cloning tau2-bench. Replaces a small set of
files inside the cloned tau2-bench/ with no-op stubs so that importing
``tau2.runner`` does not eagerly load subpackages we don't need for the
banking_knowledge text eval.

Usage:  python3 _setup.py <path/to/tau3-bench>
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

EMPTY_INIT = '"""Stubbed (text-only setup)."""\n'

LEAF_STUBS: dict[str, str] = {
    # path-relative-to-src: file content
    "tau2/voice/synthesis/conversation_builder.py": dedent('''\
        """Stubbed (text-only setup)."""
        def generate_simulation_audio(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/voice/synthesis/audio_effects/noise_generator.py": dedent('''\
        """Stubbed (text-only setup)."""
        def create_background_noise_generator(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/voice/utils/audio_preprocessing.py": dedent('''\
        """Stubbed (text-only setup)."""
        def pad_audio_with_zeros(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        def convert_to_stereo(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        def merge_audio_datas(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/voice/utils/probability.py": dedent('''\
        """Stubbed (text-only setup)."""
        def poisson_should_trigger(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/voice/utils/audio_debug.py": dedent('''\
        """Stubbed (text-only setup)."""
        def generate_audio_debug_info(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/agent/base/voice.py": dedent('''\
        """Stubbed (text-only setup)."""
        class _Subscriptable:
            """Permissive base — supports MyClass[X, Y, Z] in class definitions."""
            def __class_getitem__(cls, item):
                return cls
            def __init_subclass__(cls, **kwargs):
                pass
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("disabled in text-only setup")
        class VoiceMixin(_Subscriptable): pass
        class VoiceState(_Subscriptable): pass
        '''),
    "tau2/agent/discrete_time_audio_native_agent.py": dedent('''\
        """Stubbed (text-only setup)."""
        def create_discrete_time_audio_native_agent(*args, **kwargs):
            raise NotImplementedError("disabled in text-only setup")
        '''),
    "tau2/user/user_simulator_streaming.py": dedent('''\
        """Stubbed (text-only setup)."""
        from tau2.user.user_simulator_base import FullDuplexUser, UserState
        class VoiceStreamingUserSimulator(FullDuplexUser):
            def __init__(self, *args, **kwargs):
                raise NotImplementedError("disabled in text-only setup")
            def get_init_state(self, *args, **kwargs):
                raise NotImplementedError
            async def get_next_chunk(self, *args, **kwargs):
                raise NotImplementedError
            def is_stop(self, *args, **kwargs):
                return True
            def stop(self, *args, **kwargs):
                pass
        '''),
}

# Empty out package __init__.py files to prevent eager submodule loading.
EMPTY_INITS = [
    "tau2/voice/__init__.py",
    "tau2/voice/utils/__init__.py",
    "tau2/voice/synthesis/__init__.py",
    "tau2/voice/synthesis/audio_effects/__init__.py",
    "tau2/voice/transcription/__init__.py",
    "tau2/voice/audio_native/__init__.py",
]


def patch_agent_init(src_dir: Path) -> None:
    """Remove unused realtime imports from tau2/agent/__init__.py."""
    p = src_dir / "tau2/agent/__init__.py"
    text = p.read_text()
    for line in (
        "from tau2.voice.audio_native.openai import OpenAIRealtimeProvider\n",
        "from tau2.voice.audio_native.openai.provider import OpenAIVADMode\n",
    ):
        text = text.replace(line, "")
    text = text.replace('    "OpenAIRealtimeProvider",\n', "")
    text = text.replace('    "OpenAIVADMode",\n', "")
    p.write_text(text)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 _setup.py <path/to/tau3-bench>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1]) / "src"
    if not src.is_dir():
        print(f"error: {src} is not a directory", file=sys.stderr)
        return 1

    for rel in EMPTY_INITS:
        path = src / rel
        if path.exists():
            path.write_text(EMPTY_INIT)

    for rel, content in LEAF_STUBS.items():
        path = src / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    patch_agent_init(src)
    print(f"patched {len(EMPTY_INITS) + len(LEAF_STUBS) + 1} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
