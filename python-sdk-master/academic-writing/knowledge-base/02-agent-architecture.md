# Agent架构知识库

## 一、Agent类型分类

### 1. 角色型Agent（Role-based）
**来源：** CrewAI, HeShen-1
```
Agent(role="研究员", goal="搜索并分析文献", backstory="10年经验的环境科学研究者")
```
**优点：** 直觉映射科研团队角色，YAML可配置
**缺点：** 灵活性受限于预定义角色

### 2. 对话型Agent（Conversational）
**来源：** AG2/AutoGen
```
ConversableAgent(name, system_message, llm_config)
```
**优点：** 灵活，支持任意对话模式
**缺点：** 需要自定义编排逻辑

### 3. 图节点型Agent（Graph Node）
**来源：** LangGraph
```
Node: function(state) -> new_state
Edge: condition(state) -> next_node
```
**优点：** 最灵活，支持任意拓扑
**缺点：** 学习曲线高，需要显式状态管理

### 4. Skill型Agent（Skills-first）
**来源：** NORA (Claude Code)
```
Markdown skill files → Claude reads and executes
```
**优点：** 无需自定义服务器，天然LLM友好
**缺点：** 绑定Claude Code，调试困难

---

## 二、多Agent编排模式

### 模式1：顺序流水线（Sequential）
```
A → B → C → D
```
**来源：** CrewAI Sequential, HeShen-1
**适用：** 线性工作流（文献搜索→分析→写作）
**实现：** CrewAI Task链, LangGraph线性边

### 模式2：层级委派（Hierarchical）
```
    Manager
   /   |   \
  A    B    C
```
**来源：** CrewAI Hierarchical, HeShen-1
**适用：** 需要任务分解和质量控制
**实现：** CrewAI process=hierarchical

### 模式3：并行+合并（Parallel + Merge）
```
    Split
   /  |  \
  A   B   C
   \  |  /
    Merge
```
**来源：** HalfSeed, NORA
**适用：** 多角度并行研究（分析+数值+文献）
**实现：** LangGraph并行节点, CrewAI并行Task

### 模式4：对抗评审（Adversarial Review）
```
Writer → Critic → Writer → Critic → ...
```
**来源：** NORA (4轮), HalfSeed (Skeptic)
**适用：** 论文质量保证，多轮迭代改进
**实现：** LangGraph循环边, NORA review-loop skill

### 模式5：去中心化Swarm
```
A ↔ B ↔ C
↕   ↕   ↕
D ↔ E ↔ F
```
**来源：** OpenCLAW
**适用：** 大规模分布式协作
**实现：** P2P Gun.js同步

### 模式6：Generator-Evaluator分离
```
Generator Context ≠ Evaluator Context
Writer(context_1) → Reviewer(context_2)
```
**来源：** NORA paper-review-loop
**适用：** 避免评审者看到写作过程，更客观
**实现：** 不同Agent使用不同上下文窗口

---

## 三、记忆机制

### 短期记忆
- **对话历史：** 所有框架默认支持
- **上下文传递：** CrewAI inputs dict, LangGraph state
- **Task输出：** CrewAI task output → 下一个task

### 长期记忆
- **检查点：** LangGraph checkpointer（故障恢复+跨会话）
- **知识文件：** NORA MEMORY.md, domain knowledge files
- **数据库：** HalfSeed SQLite, LangGraph persistent store
- **Git历史：** HalfSeed每次编辑commit

### 项目级记忆
- **handoff.json：** NORA跨会话状态传递
- **TELEMETRY.jsonl：** NORA性能追踪
- **PI-LOCK：** HalfSeed保护用户编辑

---

## 四、评审评分系统

### NORA评分系统（最成熟）
| 维度 | 权重 | 硬门槛 | 含义 |
|------|------|--------|------|
| Novelty | 30% | >=6.5 | 创新性 |
| Rigor | 25% | >=7.0 | 严谨性 |
| Literature Coverage | 20% | >=6.5 | 文献覆盖 |
| Clarity | 15% | >=6.0 | 清晰度 |
| Impact | 10% | >=6.0 | 影响力 |
| **接受** | 均分>=7.5 | 全部达标 | - |

### CAJAL Tribunal系统（10维度）
新颖性、方法论、引用质量、论证强度、可重复性、清晰度、技术深度、整体可发表性、原创性、影响力

### 通用评审维度建议
对于环境科学论文：
1. 科学性（30%）- 方法正确、数据可靠
2. 创新性（25%）- 新发现、新方法
3. 文献支撑（20%）- 引用充分、对比充分
4. 逻辑性（15%）- 论证链完整
5. 可读性（10%）- 表达清晰
