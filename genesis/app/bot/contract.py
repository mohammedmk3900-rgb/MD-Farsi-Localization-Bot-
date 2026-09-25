COMMANDS = {
    "project": {
        "status": "project.read",
        "health": "health.read",
        "sync": "sync.run",
    },
    "tasks": {
        "list": "tasks.self",
        "create": "tasks.manage",
        "claim": "tasks.self",
        "submit": "tasks.self",
        "complete": "tasks.review",
    },
    "translation": {
        "check": "translation.check",
        "review": "translation.review",
    },
    "glossary": {
        "show": "glossary.read",
    },
}
