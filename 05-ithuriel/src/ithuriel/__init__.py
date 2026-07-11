"""Ithuriel 差异化层（『建』半边）——把借来后端的真跑数据升成可审计/可复现的保证结论。

阶段一最薄切片：flat run JSON → 结构化 Finding + 证据 manifest + scope 声明 + ComparisonSpec。
形状据真实摩擦（results/d8_bare_vs_defended.json）反推，不提前按论文设计。见 docs/adr/0004-*。
"""
