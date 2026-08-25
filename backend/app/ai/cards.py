"""实体卡片 md 渲染器（分区对齐实体卡片模板：客户/项目/公司）。"""


def _line(label: str, value: object) -> str:
    v = "" if value is None else str(value).strip()
    if not v or v == "待确认":
        return f"**{label}：** 待确认"
    return f"**{label}：** {v}"


def _join(items: object) -> str:
    if isinstance(items, list):
        return "、".join(str(i) for i in items if i)
    return str(items or "")


def _link(items: object) -> str:
    """把列表转成可读关联（不造真实链接，仅文本）。"""
    return _join(items) or "待确认"


def render_customer_card(card: dict, source_id: int | None) -> str:
    name = card.get("name") or "未命名"
    role = card.get("role") or ""
    lines = [f"# {name} ({role})" if role else f"# {name}"]
    lines.append(f"> 等级：{card.get('level') or 'C'} | 情报优先级：{card.get('intelligence_priority') or '待确认'}")
    lines.append("")
    lines.append("## 💼 职业属性")
    for k, label in [("company", "公司"), ("position", "岗位"), ("professional_advantages", "专业优势"), ("career_background", "职业背景")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    lines.append("## 💡 个人画像")
    for k, label in [("personality", "性格"), ("hobbies", "爱好"), ("family", "家庭"), ("habits", "习惯")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    lines.append("## 🧠 行事风格")
    for k, label in [("work_style", "做事风格"), ("decision", "决策风格"), ("communication", "沟通偏好"), ("negotiation", "谈判风格"), ("goals", "目标计划")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    lines.append("## 💬 项目看法")
    lines.append(card.get("project_views") or "待确认")
    if card.get("personal_ideas"):
        lines.append("")
        lines.append(card["personal_ideas"])
    lines.append("")
    lines.append("## 🎯 行动指南")
    for k, label in [("decision_authority", "决策权"), ("value_offer", "价值标签"), ("intelligence_priority", "情报优先级")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    lines.append("## 🔗 关联")
    lines.append(_line("项目", _link(card.get("linked_projects"))))
    lines.append(_line("公司", _link(card.get("linked_companies"))))
    lines.append(_line("来源", f"会议#{source_id}" if source_id else "待确认"))
    quotes = [q for q in (card.get("quotes") or []) if q]
    if quotes:
        lines.append("")
        lines.append("## 💬 关键语录")
        for q in quotes:
            lines.append(f"> {q}")
    return "\n".join(lines)


def render_project_card(card: dict, source_id: int | None) -> str:
    name = card.get("name") or "未命名"
    lines = [f"# {name}"]
    lines.append(f"> 状态：{card.get('status') or '待确认'} | 预算：{card.get('budget') or '待确认'}")
    lines.append("")
    lines.append("## 📖 项目背景")
    lines.append(card.get("background") or "待确认")
    lines.append("")
    lines.append("## 👥 利益相关人地图")
    lines.append(card.get("stakeholder_map") or "待确认")
    lines.append("")
    lines.append("## 🎯 决策记录")
    lines.append(card.get("decisions") or "待确认")
    lines.append("")
    lines.append("## ⚡ 当前争议点")
    lines.append(card.get("controversies") or "暂无")
    lines.append("")
    lines.append("## 📋 时间线与里程碑")
    for k, label in [("start_date", "开始日期"), ("end_date_est", "预计完工"), ("timeline", "时间线"), ("current_phase", "当前阶段"), ("key_milestones", "关键里程碑")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    rm = card.get("role_map") or {}
    lines.append("## 🏗️ 角色关系表")
    lines.append("| 角色 | 负责方 |")
    lines.append("|------|--------|")
    for r in ["developer", "builder", "architect", "facade_engineer", "facade_supplier", "supervisor"]:
        label = {"developer": "开发商", "builder": "总包", "architect": "建筑师", "facade_engineer": "幕墙工程师", "facade_supplier": "幕墙供应商", "supervisor": "监理"}[r]
        lines.append(f"| {label} | {rm.get(r) or '待确认'} |")
    lines.append("")
    lines.append("## 🔗 关联")
    lines.append(_line("人物", _link(card.get("linked_people"))))
    lines.append(_line("公司", _link(card.get("linked_companies"))))
    lines.append(_line("来源", f"会议#{source_id}" if source_id else "待确认"))
    return "\n".join(lines)


def render_company_card(card: dict, source_id: int | None) -> str:
    name = card.get("name") or "未命名"
    lines = [f"# {name}"]
    lines.append(f"> 等级：{card.get('level') or 'C'} | 区域：{card.get('region') or '待确认'}")
    lines.append("")
    lines.append("## 🏢 企业信息")
    for k, label in [("region", "区域"), ("established", "成立时间"), ("employees", "员工规模"), ("market_position", "市场定位")]:
        lines.append(_line(label, card.get(k)))
    lines.append(_line("竞品对手", _join(card.get("competitors"))))
    lines.append("")
    lines.append("## 👥 组织与团队")
    lines.append(card.get("org_structure") or "待确认")
    lines.append("")
    lines.append("## 🏗️ 项目管线与合作生态")
    lines.append(card.get("pipeline_ecology") or "待确认")
    lines.append("")
    lines.append("## ⚙️ 运营模式")
    lines.append(card.get("operation_model") or "待确认")
    lines.append("")
    lines.append("## 🎯 行动指南")
    for k, label in [("pain_points", "痛点"), ("entry_point", "切入点"), ("cooperation_path", "合作路径")]:
        lines.append(_line(label, card.get(k)))
    lines.append("")
    lines.append("## 🔗 关联")
    lines.append(_line("人物", _link(card.get("linked_people"))))
    lines.append(_line("项目", _link(card.get("linked_projects"))))
    lines.append(_line("来源", f"会议#{source_id}" if source_id else "待确认"))
    return "\n".join(lines)


def render_entity_card(entity_type: str, card: dict, source_id: int | None) -> str:
    if entity_type == "customer":
        return render_customer_card(card, source_id)
    if entity_type == "project":
        return render_project_card(card, source_id)
    return render_company_card(card, source_id)
