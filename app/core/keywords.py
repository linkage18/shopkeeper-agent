"""共享关键词抽取工具

统一 DataAgent 和 RagAgent 中的 jieba 关键词抽取逻辑。
"""
from __future__ import annotations

from typing import List

import jieba.analyse


# 只保留更可能承载业务含义的词性，减少检索噪声
_KEYWORD_ALLOW_POS = (
    "n",   # 名词: 商品、订单、销售额
    "nr",  # 人名: 张三、李四
    "ns",  # 地名: 华北、北京、上海
    "nt",  # 机构团体名: 门店、品牌、渠道
    "nz",  # 其他专有名词: SKU、GMV、AOV
    "v",   # 动词: 统计、对比、查询
    "vn",  # 名动词: 销售、成交、退款
    "a",   # 形容词: 新增、有效、活跃
    "an",  # 名形词: 可用、有效、异常
    "eng", # 英文: GMV、SKU、ROI
    "i",   # 成语或习用语
    "l",   # 常用固定短语
)


def extract_keywords(query: str) -> List[str]:
    """从查询文本中抽取关键词（TF-IDF + 词性过滤），保留原始查询作为兜底"""
    keywords = jieba.analyse.extract_tags(query, allowPOS=_KEYWORD_ALLOW_POS)
    return list(set(keywords + [query]))
