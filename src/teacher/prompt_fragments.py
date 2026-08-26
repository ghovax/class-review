"""Shared prompt fragments."""

from teacher.prompts import Prompts


def render_language_policy(prompts: Prompts) -> str:
    """Render the shared language policy."""

    return prompts.render("language_policy")
