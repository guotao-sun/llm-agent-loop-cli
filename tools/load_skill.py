"""load_skill：按名字取出某个技能（skills/ 下 SKILL.md）的正文。

技能和工具的区别：
- 工具返回的是"数据"（档案、归档片段）；
- 技能返回的是"做法"（步骤、检查项、坑），取回来是让它进上下文，指导后面怎么干。
"""

NAME = "load_skill"
DESCRIPTION = ("按名字加载一个技能的完整操作流程（SKILL.md 正文）。"
               "系统提示里只列了技能名和一句话说明，要按固定流程办事时先调它取正文。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "技能名，见系统提示里的【可用技能】"},
    },
    "required": ["name"],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    name = (args.get("name") or "").strip()
    skills = (ctx or {}).get("skills") or []
    for s in skills:
        if s["name"] == name:
            return "[skill %s]\n%s" % (name, s["body"])
    return "[error] unknown skill %r; available: %s" % (
        name, ", ".join(s["name"] for s in skills) or "none")
