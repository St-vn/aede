"""
Ask-user tools for aede.

These tools allow the agent to request input from the user mid-task without
going through the approval gate.  The actual I/O is handled by the
AskUserBackend wired into AgentLoop; the implementations here are stubs that
return immediately because the agent loop intercepts these tools before
calling the registry.

Tool overview:
- ask_user: free-form text question (legacy alias for question/text).
- ask_user_choices: pick one option from a list (legacy alias for question/single_choice).
- ask_user_confirm: yes/no question (legacy alias for question/confirm).
- question: unified tool supporting text, single_choice, multi_select, and
  confirm question types, plus multiple questions in one call.
"""
from __future__ import annotations


def ask_user(args: dict) -> str:
    question = args.get("question", "")
    return f"[ask_user will be handled by agent loop: {question}]"


def ask_user_choices(args: dict) -> str:
    question = args.get("question", "")
    return f"[ask_user_choices will be handled by agent loop: {question}]"


def ask_user_confirm(args: dict) -> str:
    question = args.get("question", "")
    return f"[ask_user_confirm will be handled by agent loop: {question}]"


def question(args: dict) -> str:
    """Unified user-question tool stub.

    The agent loop intercepts this tool and routes it to the active
    AskUserBackend.  The implementation here is only reached in tests or
    unexpected fall-through paths.
    """
    questions = args.get("questions", [])
    first = questions[0] if questions else {}
    qtext = first.get("question", "") if isinstance(first, dict) else ""
    return f"[question will be handled by agent loop: {qtext}]"
