"""
Function tools definitions for OpenAI Assistants API.
These are the standard function calling tools available to all assistants.
"""

def get_function_tools() -> list:
    """
    Returns the standard function calling tools.
    These should be added to assistants at creation time.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "handoff_to_human",
                "description": "Transfer the conversation to a human agent when the user explicitly requests to speak with a human, needs complex help, or is frustrated",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Why the handoff is needed"
                        }
                    },
                    "required": ["reason"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_link",
                "description": "Provide a URL link to the user for additional resources, documentation, or pages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full URL to send"
                        },
                        "description": {
                            "type": "string",
                            "description": "What this link is for"
                        }
                    },
                    "required": ["url", "description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Send details via email to the user when they request information to be emailed",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email content"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        }
    ]

