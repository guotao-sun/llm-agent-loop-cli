"""get_profile：读长期档案（L3）里的生效事实。"""

NAME = "get_profile"
DESCRIPTION = ("读取长期档案里的生效事实（职业、技术栈、习惯、偏好）。"
               "回答涉及用户画像时先调它，不要凭印象猜。")
PARAMETERS = {"type": "object", "properties": {}, "additionalProperties": False}


def run(store, args, ctx=None):
    facts = sorted(store.active_facts(), key=lambda e: e.get("updated_at", ""), reverse=True)
    if not facts:
        return "(profile empty)"
    return "\n".join("- %s topic=%s conf=%.2f %s"
                     % (e["id"], e.get("topic") or "-", e.get("confidence", 0), e["content"])
                     for e in facts)
