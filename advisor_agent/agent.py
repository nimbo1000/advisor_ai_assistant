from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from .llm import get_llm
from .vectorstore import retrieve_relevant_context
from .tools import TOOLS as TOOL_DEFS, schedule_calendar_event, send_email

def schedule_calendar_event_wrapper(args, creds_data=None):
    """
    Wrapper to map agent arguments to the schedule_calendar_event function.
    Accepts either a JSON string, dict, or positional args and maps them to the correct parameters.
    """
    import json
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            # If not JSON, treat as summary only
            return schedule_calendar_event(1, args, '', '', creds_data=creds_data)
    if isinstance(args, dict):
        summary = args.get('summary', '')
        start = args.get('start', '')
        end = args.get('end', '')
        attendees = args.get('attendees')
        description = args.get('description')
        location = args.get('location')
        timezone = args.get('timezone', 'UTC')
        return schedule_calendar_event(1, summary, start, end, attendees, description, location, timezone, creds_data=creds_data)
    # If it's a list or tuple, try to unpack
    if isinstance(args, (list, tuple)):
        return schedule_calendar_event(1, *args, creds_data=creds_data)
    # Fallback
    return schedule_calendar_event(1, str(args), '', '', creds_data=creds_data)

def send_email_wrapper(args, creds_data=None):
    import json
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return send_email(1, args, '', '', creds_data=creds_data)
    if isinstance(args, dict):
        to = args.get('to', '')
        subject = args.get('subject', '')
        body = args.get('body', '')
        cc = args.get('cc')
        bcc = args.get('bcc')
        attachments = args.get('attachments')
        return send_email(1, to, subject, body, cc, bcc, attachments, creds_data=creds_data)
    if isinstance(args, (list, tuple)):
        return send_email(1, *args, creds_data=creds_data)
    return send_email(1, str(args), '', '', creds_data=creds_data)

# Convert each entry in tools.py's TOOLS list to a Langchain Tool
langchain_tools = []
for tool_def in TOOL_DEFS:
    # Support both 'function' and 'func' keys for backward compatibility
    func = tool_def.get('function') or tool_def.get('func')
    name = tool_def['name']
    # Use the wrapper for schedule_calendar_event and send_email
    if name == 'schedule_calendar_event':
        func = schedule_calendar_event_wrapper
    if name == 'send_email':
        func = send_email_wrapper
    langchain_tools.append(
        Tool(
            name=name,
            func=func,
            description=tool_def['description']
        )
    )

llm = get_llm()

agent_executor = initialize_agent(
    langchain_tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)

def agent_respond(user_id, message, creds_data=None):
    # Patch the schedule_calendar_event and send_email tools to always use creds_data
    for tool in langchain_tools:
        if tool.name == 'schedule_calendar_event':
            tool.func = lambda args: schedule_calendar_event_wrapper(args, creds_data=creds_data)
        if tool.name == 'send_email':
            tool.func = lambda args: send_email_wrapper(args, creds_data=creds_data)
    response = agent_executor.run(message)
    return response 