#!/usr/bin/env python3
"""
生成软著申请材料（Word文档）
- 软件说明书（.docx）
- 源代码文档（.docx）
- 信息采集表（.doc 格式，实际为 .docx）

配合 generate_screenshots.py 生成的截图 HTML 页面使用。
用户需自行用浏览器打开 HTML 页面截图，插入到说明书对应位置。
"""

import os
import sys
import json
from datetime import datetime

# Windows 控制台默认 GBK，强制 UTF-8 避免打印 emoji/中文崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "软著申请材料")
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")


def add_heading(doc, text, level=1):
    """添加标题，保持格式一致。"""
    h = doc.add_heading(text, level=level)
    return h


def add_para(doc, text, bold=False, font_size=None, align=None):
    """添加段落。"""
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    run = p.add_run(text)
    if bold:
        run.bold = True
    if font_size:
        run.font.size = Pt(font_size)
    return p


def add_bullet(doc, text):
    """添加项目符号段落。"""
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(text)
    return p


def generate_manual():
    """生成软件说明书（排版与参考文件一致）。"""
    doc = Document()

    # ─── 页面设置（Letter 纸，边距上下2.5cm 左右3.2cm）───
    for section in doc.sections:
        section.page_width = Cm(21.6)
        section.page_height = Cm(27.9)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.2)
        section.right_margin = Cm(3.2)

    # ─── 全局样式（与参考文件一致）────────────────────────
    # Normal: Times New Roman 12pt, 1.5倍行距, 首行缩进2字符(304800 EMU)
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5
    style.paragraph_format.first_line_indent = 304800

    # Heading 1: 22pt 加粗 黑色
    h1 = doc.styles['Heading 1']
    h1.font.name = 'Times New Roman'
    h1.font.size = Pt(22)
    h1.font.bold = True
    h1.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    h1.paragraph_format.space_after = Pt(0)

    # Heading 2: 16pt
    h2 = doc.styles['Heading 2']
    h2.font.size = Pt(16)
    h2.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    h2.font.bold = True

    # Heading 3: 15pt 黑色
    h3 = doc.styles['Heading 3']
    h3.font.size = Pt(15)
    h3.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # ─── 封面（Heading 1 样式，居中）──────────────────────
    p = doc.add_paragraph(style='Heading 1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\n\n\n风电塔灾损测算多模态大模型可视化软件V1.0 软件说明书\n\n\n软件简介及使用说明书\n\n")
    run.bold = True

    p = doc.add_paragraph(style='Heading 1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\n\n2026年8月\n")
    run.bold = True

    # 封面后不插入分页，正文从新页开始由 Word 排版决定；
    # 参考文件封面与正文直接相连，这里用分页符分隔
    doc.add_page_break()

    # ══════════════════════════════════════════════════════
    # 一、软件概述
    # ══════════════════════════════════════════════════════
    add_heading(doc, "一、软件概述", level=2)

    # 1.1
    add_heading(doc, "1.1 软件背景", level=3)
    add_para(doc, (
        "风能是当前发展规模最大的可再生能源形式之一。截至2025年底，全国风电累计并网装机容量"
        "已超过5.5亿千瓦，陆上风电场分布范围从东部沿海扩展到高海拔山区、戈壁荒漠等环境条件"
        "复杂的区域。风电机组长期在野外环境中运行，塔筒、叶片、机舱等结构构件持续承受风荷载、"
        "温度变化、疲劳循环以及部分地区的地震作用，结构健康状况直接影响机组的运行安全与服役寿命。"
    ))
    add_para(doc, (
        "风电塔结构由基础、塔筒、机舱、轮毂和叶片等部分组成，其中塔筒通常为分段式锥形钢结构，"
        "高度可达百余米，是支撑机舱与叶片的核心承力构件。在长期服役过程中，塔筒涂层因紫外线照射、"
        "盐雾侵蚀和风雨冲刷逐渐老化，出现涂层破损后钢材表面直接暴露于腐蚀介质，可能进一步发展为"
        "局部腐蚀、壁厚减薄甚至裂纹；叶片作为受力与气动外形构件，易出现前缘侵蚀、表面开裂、"
        "雷击损伤等问题；连接法兰、焊缝等部位则是应力集中区域，疲劳裂纹风险较高。上述损伤若"
        "不能及时发现和处理，可能在极端风况下引发严重后果。"
    ))
    add_para(doc, (
        "目前风电场结构巡检主要依靠人工目视检查、无人机航拍影像判读和无损检测等手段。"
        "人工目视检查依赖巡检人员经验，判读标准不统一，且高空部位检查作业风险较高；"
        "无人机航拍能够覆盖机舱、叶片等高空部位，但产生的图像数据量大，逐张人工判读耗时费力，"
        "判读结果受人员疲劳和主观因素影响明显。随着风电场规模扩大和巡检频次提高，"
        "传统人工判读方式在效率和一致性方面的不足日益突出，客观上需要自动化程度更高的"
        "图像分析手段予以支撑。"
    ))
    add_para(doc, (
        "近年来，计算机视觉技术快速发展，基于图像的目标识别与语义理解方法在工业巡检领域"
        "获得广泛应用。视觉语言理解技术能够将图像视觉特征与文本语义信息相结合，在识别"
        "图像内容的同时生成符合规范的自然语言描述，为巡检图像的自动化判读提供了新的技术路径。"
        "本软件即在此背景下开发，面向风电塔结构巡检场景，将视觉语言理解技术应用于损伤检测"
        "与评估，实现巡检图像从上传、分析到结构化报告输出的完整流程。"
    ))

    # 1.2
    add_heading(doc, "1.2 软件目的", level=3)
    add_para(doc, (
        "本软件旨在构建一套面向风电塔结构的损伤检测与评估工具，"
        "实现从巡检图像到结构化损伤报告的自动化处理，减轻人工判读负担，"
        "统一评估口径，为运维决策提供参考依据。"
    ))
    add_para(doc, "本软件的主要目的包括以下几个方面：")
    add_para(doc, (
        "面向风电塔巡检场景，提供图像化的损伤检测手段：用户上传巡检图像后，"
        "软件自动完成构件识别、损伤类型判定和风险等级评估，无需人工逐张判读。"
    ))
    add_para(doc, (
        "建立标准化的评估流程：将构件、损伤、风险、处置建议等信息组织为"
        "结构统一的JSON报告，字段定义一致，便于不同人员、不同场次巡检结果之间的比较。"
    ))
    add_para(doc, (
        "降低判读门槛：通过结构化展示和风险高亮，使不具备专业图像判读经验的"
        "运维人员也能快速理解检测结论，关注重点部位。"
    ))
    add_para(doc, (
        "支持批量处理与数据积累：提供批量检测功能满足多图巡检需求，"
        "通过历史记录管理保存检测数据，为后续统计分析提供基础。"
    ))
    add_para(doc, "综合以上开发目的，本软件旨在形成一套覆盖检测、展示、记录全流程的风电塔损伤评估工具。")

    # 1.3
    add_heading(doc, "1.3 软件特点", level=3)
    add_para(doc, "风电塔灾损测算多模态大模型可视化软件在功能设计和实现方式上具有以下特点：")
    add_para(doc, (
        "损伤检测与评估一体化：软件对巡检图像进行构件识别、损伤类型判定、"
        "风险等级评估，并将评估结论与处置建议组织在同一份报告中，"
        "一次分析即可获得完整的评估信息。"
    ))
    add_para(doc, (
        "输出结构统一：检测结果采用JSON格式组织，包含6大类23个字段的嵌套结构，"
        "涵盖构件识别、损伤判定、风险分析、运维建议、不确定性说明和结论建议，"
        "字段口径一致，便于程序化解析与后续统计。"
    ))
    add_para(doc, (
        "界面操作直观：软件提供三Tab界面布局，集成图片上传、结果展示、"
        "JSON报告查看、历史记录管理等功能，操作路径清晰，无需专门培训即可上手。"
    ))
    add_para(doc, (
        "支持批量处理：支持多张图片同时上传并逐张分析，自动生成汇总表格，"
        "适用于风电场批量巡检任务。"
    ))
    add_para(doc, (
        "数据可追溯：内置SQLite数据库自动保存每次检测记录，"
        "支持历史回看与统计汇总，检测数据可追溯、可复核。"
    ))

    # 1.4 软件技术特点
    add_heading(doc, "1.4 软件技术特点", level=3)
    add_para(doc, "本软件在技术实现上具有以下特点：")
    add_para(doc, (
        "多模态理解技术：软件以视觉语言模型为核心推理引擎，"
        "采用Gated DeltaNet混合注意力机制（每4层包含1个全注意力层和3个线性注意力层），"
        "结合视觉编码器实现图像与文本的多模态融合理解，"
        "能够对风电塔巡检图像中的构件、损伤特征进行联合分析与语义推理。"
    ))
    add_para(doc, (
        "面向任务的模型优化：模型在风电塔巡检图像数据集上进行专项训练，"
        "在2168条测试集上达到12字段Macro Accuracy 89.04%、4字段QWK 0.7471的性能，"
        "对涂层破损、腐蚀、裂纹、断裂、结构变形等常见损伤类型具有较好的识别能力。"
    ))
    add_para(doc, (
        "结构化输出与容错解析：模型直接输出严格JSON格式报告，"
        "软件内置容错解析机制，对输出进行清洗与兜底提取，确保JSON解析率达到100%，"
        "为下游程序化处理提供可靠数据接口。"
    ))
    add_para(doc, (
        "本地化推理架构：全部推理过程在本地完成，数据不出内网，"
        "支持Apple Silicon硬件加速，兼顾检测效率与数据安全。"
    ))
    add_para(doc, (
        "数据持久化与追溯：基于SQLite数据库构建检测历史存储体系，"
        "完整记录每次检测的原始结果与结构化报告，支持按ID检索回看，"
        "形成可追溯的检测数据链。"
    ))

    doc.add_page_break()

    # ══════════════════════════════════════════════════════
    # 二、基本概念与理论
    # ══════════════════════════════════════════════════════
    add_heading(doc, "二、基本概念与理论", level=2)

    # 2.1
    add_heading(doc, "2.1 风电塔结构及其损伤类型", level=3)
    add_para(doc, (
        "风电塔结构是风电机组的主要承力体系，通常包括基础、塔筒、机舱、轮毂与叶片等部分。"
        "塔筒多采用分段式锥形钢结构，各段之间通过法兰和高强度螺栓连接；机舱内布置传动与"
        "发电设备，承受风轮传递的载荷；叶片是捕风部件，外形决定气动性能。各构件的损伤形式"
        "与受力特点密切相关。"
    ))
    add_para(doc, "本软件涉及的构件类别与常见损伤类型如下：")
    add_para(doc, (
        "塔筒结构：包括塔筒筒体、法兰连接、焊缝及门洞等部位。"
        "常见损伤为涂层破损、钢材腐蚀、壁厚减薄、焊缝裂纹、结构变形等。"
    ))
    add_para(doc, (
        "叶片结构：包括叶片壳体、前缘、后缘及叶根连接区。"
        "常见损伤为前缘侵蚀、表面开裂、涂层剥落、雷击损伤、结构变形等。"
    ))
    add_para(doc, (
        "机舱结构：包括机舱罩、底座及内部设备支架。"
        "常见损伤为罩体开裂、涂层老化、连接件松动等。"
    ))
    add_para(doc, (
        "附属设施：包括爬梯、平台、护栏、避雷系统等。"
        "常见损伤为涂层破损、构件锈蚀、连接松动等。"
    ))
    add_para(doc, (
        "从损伤发展过程看，涂层破损通常是损伤演化的起点，涂层失效后钢材或复合材料"
        "直接暴露于环境介质，进而发展出腐蚀、裂纹等更严重的损伤形式。因此巡检评估中"
        "既关注当前损伤状态，也关注损伤发展趋势，为运维计划安排提供依据。"
    ))

    # 2.2
    add_heading(doc, "2.2 视觉语言理解技术", level=3)
    add_para(doc, (
        "视觉语言理解技术是计算机视觉与自然语言处理相结合的技术方向，"
        "其核心在于让模型同时理解图像中的视觉内容与文本语义信息。"
        "本软件采用Qwen3.5-4B视觉语言模型作为推理引擎，"
        "模型由视觉编码器与文本解码器两部分组成。"
    ))
    add_para(doc, (
        "视觉编码器负责将输入图像转换为视觉特征序列。模型采用ViT结构，"
        "输入图像被划分为固定尺寸的图像块（patch），每个图像块经线性映射后"
        "与位置编码相加，再经过多层Transformer编码得到视觉特征。"
        "文本解码器采用Gated DeltaNet混合注意力机制，每4层中包含1个全注意力层"
        "和3个线性注意力层，线性注意力以线性复杂度处理长序列，"
        "兼顾了长上下文建模能力与计算效率。"
    ))
    add_para(doc, (
        "在推理时，图像经视觉编码器得到视觉特征，与用户输入的文本指令"
        "一起送入解码器，模型逐步生成评估文本。由于模型在风电塔巡检图像"
        "数据集上经过专项训练，其输出内容能够贴合巡检评估任务的要求，"
        "按照预设的字段结构组织评估结论。"
    ))

    # 2.3
    add_heading(doc, "2.3 结构化报告格式", level=3)
    add_para(doc, (
        "本软件采用JSON（JavaScript Object Notation）格式组织检测报告。"
        "JSON是一种轻量级的数据交换格式，采用键值对与嵌套结构描述数据，"
        "具有结构清晰、易于解析、跨语言通用的特点。"
    ))
    add_para(doc, (
        "检测报告整体划分为6大类：图像Caption（图像质量评价与简要描述）、"
        "构件识别（构件名称与所属系统）、损伤判定（是否可判定、是否存在损伤、"
        "损伤类型、发展趋势等）、潜在风险影响分析（对结构安全、运行可靠性与"
        "长期寿命的影响）、运维与处置建议（是否建议停机、短期处置、中长期修复等）、"
        "不确定性说明与调查建议、结论建议（置信度与巡检优先级）。"
        "每类下包含若干具体字段，全部字段共23个。"
    ))
    add_para(doc, (
        "结构化报告的优点在于：字段含义明确、取值规范（如巡检优先级取值低/中/高，"
        "是/否类问题取值是/否），既便于人工阅读，也便于程序化处理，"
        "可直接存入数据库或导入统计分析工具。"
    ))

    # 2.4
    add_heading(doc, "2.4 软件处理流程", level=3)
    add_para(doc, "软件的处理流程如图1所示：")
    add_para(doc, "图1 软件处理流程图", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, (
        "完整的处理流程包括以下环节：用户上传风电塔巡检图片，软件对图片进行"
        "尺寸归一化等预处理后送入推理引擎，模型输出结构化JSON报告，"
        "前端解析报告并按字段分类展示检测结果，同时自动保存到历史数据库，"
        "用户可查看完整JSON或导出Markdown/JSON格式报告。"
    ))
    add_para(doc, (
        "从上传图片到获得检测报告，全流程无需人工干预。单张图片的推理过程"
        "在本地完成，处理耗时与图像内容复杂度相关，平均耗时在1分钟以内。"
    ))

    doc.add_page_break()

    # ══════════════════════════════════════════════════════
    # 三、软件功能
    # ══════════════════════════════════════════════════════
    add_heading(doc, "三、软件功能", level=2)

    add_para(doc, (
        "本软件是一款面向风电塔结构损伤检测的工具，"
        "能够对风电塔巡检图像进行分析和结构化评估。"
        "软件主界面包括三个功能Tab：单图检测、批量检测和历史记录，"
        "用户可通过图形界面完成从图片上传到结果导出的完整流程。"
    ))

    # 3.1
    add_heading(doc, "3.1 用户主界面", level=3)
    add_para(doc, (
        "软件主界面为统一的可视化操作界面，顶部显示软件名称与联合开发单位，"
        "下方为三Tab功能切换面板，各Tab分别承载不同的检测任务。"
        "界面整体采用左右分栏布局，左侧为操作区，右侧为结果展示区，"
        "布局清晰，操作流程明确。"
    ))
    add_para(doc, "图2 用户主界面展示", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, (
        "主界面左侧为图片上传区和控制按钮区，包含图片上传组件、示例图片入口、"
        "分析按钮、清空按钮、状态显示栏以及报告导出按钮；"
        "右侧为检测结果展示区，用于显示检测摘要、分栏检测结果和完整JSON报告。"
        "用户可通过拖拽或点击上传图片，也可点击示例图片快速体验，"
        "点击「开始分析」按钮启动分析，结果在右侧分栏展示。"
    ))

    # 3.2
    add_heading(doc, "3.2 单图检测功能", level=3)
    add_para(doc, (
        "单图检测是本软件的核心功能模块，用于对单张风电塔巡检图像进行完整评估。"
        "操作流程为：上传图片，点击「开始分析」，等待推理完成后查看检测结果。"
    ))
    add_para(doc, (
        "检测结果以结构化方式分栏展示，包括：构件识别（构件名称、所属系统）、"
        "损伤判定（是否可判定、是否存在损伤、损伤类型、损伤发展趋势、"
        "损伤分布位置与范围、关键视觉证据描述等）、"
        "潜在风险影响分析（对结构安全性的影响程度、对运行可靠性的影响、"
        "对长期服役寿命的影响）、运维与处置建议（是否建议停机、短期处置建议、"
        "中长期修复建议、后续巡检关注问题）、不确定性说明与调查建议、"
        "结论建议（置信度、巡检优先级）。"
    ))
    add_para(doc, (
        "对高风险结果（如检测到断裂、巡检优先级为高、建议停机）自动以红色横幅"
        "和红色字体高亮标记，提示用户重点关注；正常结果以绿色标记。"
        "用户可通过折叠面板查看完整JSON报告，核对各字段的原始输出。"
    ))
    add_para(doc, "图3 高风险检测结果展示", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "图4 正常检测结果展示", align=WD_ALIGN_PARAGRAPH.CENTER)

    # 3.3
    add_heading(doc, "3.3 批量检测功能", level=3)
    add_para(doc, (
        "批量检测模块面向多图巡检场景，支持用户一次上传多张巡检图片，"
        "软件逐张进行分析并汇总结果。操作流程为：在批量检测Tab中"
        "选择多张图片，点击「开始批量分析」，等待全部图片处理完成后查看汇总结果。"
    ))
    add_para(doc, (
        "汇总结果以表格形式展示，每行对应一张图片，包含风险状态、损伤情况、"
        "损伤类型、构件名称、巡检优先级和推理耗时等信息，"
        "高风险图片在表格中以红色标记，便于快速定位重点关注对象。"
    ))
    add_para(doc, "图5 批量检测结果展示", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, (
        "批量检测的每张图片结果也附带详细的结构化展示，便于用户逐张复核。"
        "该功能适用于风电场批量巡检任务，可显著减少逐张操作的时间。"
    ))

    # 3.4
    add_heading(doc, "3.4 历史记录与统计功能", level=3)
    add_para(doc, (
        "每次检测的结果自动保存到本地SQLite数据库（history.db），"
        "历史记录Tab提供完整的记录管理和统计功能，包括统计面板、"
        "历史记录表和详情查看三部分。"
    ))
    add_para(doc, "图6 历史记录与统计面板", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, (
        "统计面板显示总检测数、高风险数、发现损伤数和正常数四个核心指标，"
        "便于用户快速掌握整体检测情况。历史记录表按时间倒序排列，"
        "记录ID、检测时间、图片名称、风险状态、损伤情况、损伤类型、构件、"
        "优先级、置信度和耗时等信息，高风险记录自动红色高亮。"
        "用户可通过输入记录ID查看该次检测的完整结果与JSON报告，"
        "实现历史数据的追溯复核。"
    ))

    # 3.5
    add_heading(doc, "3.5 报告导出功能", level=3)
    add_para(doc, (
        "软件支持将检测报告导出为Markdown和JSON两种格式，"
        "便于检测结果的归档、传递与二次分析。"
    ))
    add_para(doc, (
        "Markdown格式报告包含检测时间、图片名称、推理耗时等基本信息，"
        "以及按6大类组织的评估字段，适合直接阅读和嵌入巡检报告文档；"
        "JSON格式报告在原始检测结果基础上附加导出时间和图片信息，"
        "适合程序化处理和批量统计分析。导出文件由软件自动生成，"
        "用户可直接下载保存。"
    ))
    add_para(doc, "图7 JSON报告详情展示", align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_page_break()

    # ══════════════════════════════════════════════════════
    # 四、生成结果展示
    # ══════════════════════════════════════════════════════
    add_heading(doc, "四、生成结果展示", level=2)

    add_heading(doc, "4.1 输出格式", level=3)
    add_para(doc, (
        "本软件完成检测后，自动生成结构化JSON格式的评估报告，"
        "同时支持导出为Markdown格式方便阅读。JSON报告采用嵌套结构，"
        "外层按评估类别划分，内层为具体字段，整体格式规范统一，"
        "为后续报告整理、数据分析和研究提供基础数据支持。"
    ))
    add_para(doc, (
        "输出的JSON报告可直接保存为文件，也可由软件解析后以分栏形式展示。"
        "两种形态内容一致，满足不同使用场景的需求。"
    ))

    add_heading(doc, "4.2 字段说明", level=3)
    add_para(doc, "JSON报告包含6大类23个字段，主要字段含义如下：")

    # 用表格展示字段说明
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Medium Shading 1 Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    hdr[0].text = "大类"
    hdr[1].text = "字段"
    hdr[2].text = "说明"

    fields = [
        ("图像Caption", "简要", "图像简要描述"),
        ("图像Caption", "图像质量评价", "清晰/一般/模糊"),
        ("1. 构件识别", "构件名称", "识别的构件名称"),
        ("1. 构件识别", "构件所属系统", "所属系统分类"),
        ("2. 损伤判定", "是否可判定", "是/否"),
        ("2. 损伤判定", "是否存在损伤", "是/否"),
        ("2. 损伤判定", "损伤类型", "无损伤/涂层破损/腐蚀/裂纹/断裂/结构变形等"),
        ("2. 损伤判定", "损伤发展趋势", "稳定/恶化等"),
        ("3. 潜在风险影响分析", "对结构安全性的影响程度", "无/低/中/高"),
        ("3. 潜在风险影响分析", "是否对机组运行可靠性影响", "是/否"),
        ("3. 潜在风险影响分析", "是否对长期服役寿命的影响", "是/否"),
        ("4. 运维与处置建议", "是否建议停机、限功率运行或重点监测", "是/否"),
        ("4. 运维与处置建议", "短期处置建议", "文本描述"),
        ("4. 运维与处置建议", "中长期修复或改进建议", "文本描述"),
        ("4. 运维与处置建议", "后续巡检建议关注的问题", "文本描述"),
        ("5. 不确定性说明与调查建议", "是否建议补充获取更高分辨率或多角度图像", "是/否"),
        ("5. 不确定性说明与调查建议", "是否建议结合现场巡检或历史运维数据进行综合判断", "是/否"),
        ("5. 不确定性说明与调查建议", "当前是否建议仅基于该图像做出维修或停机决策", "是/否"),
        ("6. 结论建议", "巡检优先级", "低/中/高"),
        ("6. 结论建议", "本次判断的置信度", "低/中/高"),
    ]
    for section, field, desc in fields:
        row = table.add_row().cells
        row[0].text = section
        row[1].text = field
        row[2].text = desc

    add_para(doc, "")
    add_para(doc, "图8 生成结果JSON示例", align=WD_ALIGN_PARAGRAPH.CENTER)

    # 4.3
    add_heading(doc, "4.3 结果应用场景", level=3)
    add_para(doc, "本软件生成的检测报告可应用于以下场景：")
    add_para(doc, (
        "日常巡检辅助：巡检人员现场或事后对拍摄图像进行快速检测，"
        "获取损伤类型与巡检优先级的初步判断，辅助安排维修计划。"
    ))
    add_para(doc, (
        "巡检记录归档：批量检测结果与历史记录相结合，"
        "形成场站级的巡检台账，便于查询与追溯。"
    ))
    add_para(doc, (
        "损伤演化跟踪：对同一部位不同时期的巡检图像进行检测，"
        "结合历史记录对比损伤发展趋势，为制定检修周期提供参考。"
    ))
    add_para(doc, (
        "数据分析与研究：导出的JSON报告可直接导入统计工具，"
        "用于损伤类型分布、风险等级分布等统计分析。"
    ))

    # 保存
    path = os.path.join(OUTPUT_DIR, "软件说明书-风电塔灾损测算多模态大模型可视化软件.docx")
    doc.save(path)
    print(f"✅ 软件说明书: {path}")
    return path



def generate_source_code():
    """生成源代码文档。"""
    doc = Document()

    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(10)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\n\n风电塔灾损测算多模态大模型可视化软件\n\n软件源代码\n\n")
    run = p.add_run("\n中国华电集团有限公司 × 四川大学 联合开发\n\n")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(0x12, 0x51, 0x91)

    doc.add_page_break()

    # 上游 SFT 目录（模型评估代码）
    SFT_DIR = os.path.join(BASE_DIR, "..", "SFT")

    # 按模块分组收录代码
    code_groups = [
        {
            "title": "一、平台前端与交互模块",
            "files": [
                "app.py",
            ],
        },
        {
            "title": "二、模型推理与解析模块",
            "files": [
                "inference.py",
                "parser.py",
                "formatter.py",
                "config.py",
            ],
        },
        {
            "title": "三、数据管理与导出模块",
            "files": [
                "history.py",
                "exporter.py",
            ],
        },
        {
            "title": "四、平台测试与验证模块",
            "files": [
                "smoke_test.py",
                "batch_test.py",
            ],
        },
        {
            "title": "五、模型推理评估模块（服务器端）",
            "files": [
                os.path.join("qwen35-4b_server", "eval_model_35_4b_vllm.py"),
                os.path.join("qwen35-4b_server", "verify_chat_template.py"),
            ],
        },
        {
            "title": "六、模型评估报告生成模块（服务器端）",
            "files": [
                os.path.join("qwen35-4b_server", "eval_report.py"),
            ],
        },
    ]

    total_lines = 0
    for group in code_groups:
        add_heading(doc, group["title"], level=1)
        for fname in group["files"]:
            # 平台内文件用 BASE_DIR，SFT 文件用 SFT_DIR
            if os.path.dirname(fname):
                fpath = os.path.join(SFT_DIR, fname)
            else:
                fpath = os.path.join(BASE_DIR, fname)
            if not os.path.exists(fpath):
                print(f"  ⚠️ 文件不存在，跳过: {fpath}")
                continue

            with open(fpath, "r", encoding="utf-8") as f:
                code = f.read()
            nlines = code.count("\n") + 1
            total_lines += nlines

            # 文件名作为标题
            add_heading(doc, os.path.basename(fname), level=2)

            # 添加代码（用等宽字体）
            p = doc.add_paragraph()
            run = p.add_run(code)
            run.font.name = 'Courier New'
            run.font.size = Pt(8)

            doc.add_page_break()

    path = os.path.join(OUTPUT_DIR, "软件源代码-风电塔灾损测算多模态大模型可视化软件.docx")
    doc.save(path)
    print(f"✅ 源代码文档: {path}")
    print(f"   收录代码总行数: {total_lines}")
    return path



def generate_info_form():
    """生成信息采集表（.docx 格式，内容符合信息采集表要求）。"""
    doc = Document()

    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(12)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("计算机软件著作权信息采集表")
    run.bold = True
    run.font.size = Pt(18)

    doc.add_paragraph()

    # 表格
    info_items = [
        ("软件名称", "风电塔灾损测算多模态大模型可视化软件"),
        ("软件简称", "风电塔灾损测算软件"),
        ("版本号", "V1.0"),
        ("分类号", "30500-应用软件"),
        ("开发完成日期", "2026年08月03日"),
        ("首次发表日期", "2026年08月03日"),
        ("开发方式", "独立开发"),
        ("权利取得方式", "原始取得"),
        ("权利范围", "全部权利"),
        ("开发的硬件环境", "Apple M1 Pro处理器，16GB内存，512GB硬盘"),
        ("运行的硬件环境", "Apple M1 Pro及以上处理器，16GB内存，256GB硬盘"),
        ("开发该软件的操作系统", "macOS 15.x"),
        ("软件开发环境/开发工具", "PyCharm, Visual Studio Code"),
        ("该软件的运行平台/操作系统", "macOS 15.x"),
        ("软件运行支撑环境/支持软件", "Python 3.11, PyTorch 2.13.0, transformers 5.14.1, Gradio 6.22.0"),
        ("编程语言", "Python"),
        ("源程序量", "约5000行"),
    ]

    table = doc.add_table(rows=len(info_items), cols=2)
    table.style = 'Table Grid'
    for i, (key, value) in enumerate(info_items):
        table.rows[i].cells[0].text = key
        table.rows[i].cells[1].text = value
        # 加粗左侧列
        for p in table.rows[i].cells[0].paragraphs:
            for run in p.runs:
                run.bold = True

    doc.add_paragraph()

    # 软件用途和技术特点
    add_heading(doc, "软件用途和技术特点（200字以内）", level=3)
    add_para(doc, (
        "本软件是一款面向风电塔结构损伤检测的工具，"
        "采用视觉语言理解技术，对风电塔巡检图像进行智能分析和结构化评估。"
        "软件具有单图检测、批量分析、历史记录管理和报告导出功能，"
        "输出包含6大类23个字段的标准化JSON报告，为风电塔运维提供高效、精准的损伤检测支持。"
        "软件由中国华电集团有限公司与四川大学联合开发，支持本地化部署。"
    ))

    doc.add_paragraph()

    # 软件的技术特点
    add_heading(doc, "软件的技术特点（200字以内）", level=3)
    add_para(doc, (
        "本软件采用视觉语言理解技术实现风电塔巡检图像的智能化损伤评估，"
        "可同时处理图像与文本信息，实现构件识别、损伤类型判定与风险等级评估的"
        "一体化分析；检测结果按6大类23个字段的JSON格式输出，便于程序化解析与"
        "数据统计；推理在本机完成，数据不出内网，支持Apple Silicon硬件加速；"
        "支持多图连续分析并自动汇总，适用于批量巡检；内置SQLite数据库记录检测历史，"
        "支持结果回看与报告导出，形成数据链。"
    ))
    doc.add_paragraph()

    # 主要功能
    add_heading(doc, "主要功能", level=3)
    add_para(doc, "本软件主要功能包括：")
    add_bullet(doc, (
        "单图损伤检测：用户上传一张风电塔巡检图片后，软件调用视觉语言模型进行智能分析，"
        "自动输出完整的结构化评估报告。报告涵盖构件识别（构件名称、所属系统）、"
        "损伤判定（是否可判定、是否存在损伤、损伤类型、损伤发展趋势、损伤分布位置与范围、"
        "关键视觉证据描述、可能的成因推测）、潜在风险影响分析（对结构安全性的影响程度、"
        "对机组运行可靠性的影响、对长期服役寿命的影响）、运维与处置建议（是否建议停机、"
        "限功率运行或重点监测、短期处置建议、中长期修复建议、后续巡检关注问题）、"
        "不确定性说明与调查建议、结论建议（置信度、巡检优先级）等6大类23个字段，"
        "一次分析即可获得完整的评估信息。"
    ))
    add_bullet(doc, (
        "批量检测：支持用户同时上传多张巡检图片，软件逐张调用模型进行分析，"
        "自动生成汇总结果表格，逐条列出每张图片的风险状态、损伤情况、损伤类型、"
        "构件名称、巡检优先级和推理耗时等信息，便于批量巡检任务的整体浏览与"
        "重点关注对象定位。批量检测的每张图片结果同时附带详细的结构化展示，"
        "支持逐张复核。"
    ))
    add_bullet(doc, (
        "检测结果可视化：检测结果以分栏形式结构化展示，按图像信息、构件识别、"
        "损伤判定、风险影响分析、运维建议、不确定性说明和结论建议等区块组织，"
        "风险相关字段以红绿颜色标记，用户无需解析JSON即可直观读取关键结论。"
        "同时提供完整JSON报告的折叠查看功能，便于核对各字段的原始输出。"
    ))
    add_bullet(doc, (
        "统计图表分析：软件基于历史检测记录自动生成统计图表，包括损伤类型分布饼图、"
        "巡检优先级分布柱状图和检测数量趋势折线图，直观反映损伤类型的构成比例、"
        "风险等级分布情况和检测数据的时间变化规律，为运维决策和数据分析提供可视化支撑。"
    ))
    add_bullet(doc, (
        "历史记录管理：每次检测结果自动保存到本地SQLite数据库，"
        "历史记录界面提供统计面板（总检测数、高风险数、发现损伤数、正常数）"
        "和历史记录表，记录按时间倒序排列，高风险记录自动红色高亮；"
        "支持按记录ID查询历史检测详情，回看当时的完整结构化报告与JSON数据，"
        "实现检测数据的可追溯与复核。"
    ))
    add_bullet(doc, (
        "报告导出：支持将检测报告导出为Markdown和JSON两种格式。"
        "Markdown格式报告包含检测时间、图片名称、推理耗时等基本信息以及"
        "按6大类组织的评估字段，适合直接阅读和嵌入巡检报告文档；"
        "JSON格式报告在原始检测结果基础上附加导出时间和图片信息，"
        "适合程序化处理和批量统计分析。"
    ))
    add_bullet(doc, (
        "高风险告警：当检测结果判定为高风险（如存在断裂、巡检优先级为高、"
        "建议停机或重点监测）时，软件自动以红色横幅和红色字体高亮标记，"
        "并在历史记录中同样以红色行背景突出显示，提示用户优先关注和处理。"
    ))
    add_bullet(doc, (
        "图片信息展示：上传巡检图片后，软件自动读取并显示图片的尺寸、格式和"
        "文件大小等元信息，便于用户核对上传文件的完整性与适用性。"
    ))
    add_bullet(doc, (
        "结果复制与示例图库：提供一键复制JSON报告功能，方便用户将检测结果"
        "粘贴到其他文档或分析工具中；界面内置20张风电塔巡检示例图片，"
        "支持快速体验软件功能，无需准备测试数据即可上手使用。"
    ))

    path = os.path.join(OUTPUT_DIR, "信息采集表-风电塔灾损测算多模态大模型可视化软件.docx")
    doc.save(path)
    print(f"✅ 信息采集表: {path}")
    return path


def main():
    print("=" * 60)
    print("  生成软著申请材料")
    print("=" * 60)
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  截图目录: {SCREENSHOT_DIR}")
    print()

    manual_path = generate_manual()
    print()

    code_path = generate_source_code()
    print()

    form_path = generate_info_form()
    print()

    print("=" * 60)
    print("  生成完成！")
    print("=" * 60)
    print(f"  1. 软件说明书: {manual_path}")
    print(f"  2. 源代码文档: {code_path}")
    print(f"  3. 信息采集表: {form_path}")
    print()
    print("  截图指南：")
    print(f"    截图 HTML 文件在: {SCREENSHOT_DIR}/")
    print("    用浏览器打开每个 .html 文件，截取全屏")
    print("    将截图插入说明书对应位置（替换 图2-图8 占位）")


if __name__ == "__main__":
    main()