# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 5. Module Registration Rule (项目铁律)

**新增模块必须同时接入管线，禁止"只建不接"。**

当创建新的 Python 模块时，必须同时完成：

1. **写模块代码** — 实现功能
2. **注册到 paper_context.py** — 在 MODULE_REGISTRY 中添加条目，声明 needs/provides
3. **写接入函数** — 在 paper_context.py 中添加 `_run_xxx(ctx)` 函数
4. **运行验证** — 执行 `python check_orphans.py` 确认无孤立模块

```python
# 示例：新增 my_module.py 后，必须在 paper_context.py 中：
def _run_my_module(ctx: PaperContext):
    from my_module import MyClass
    result = MyClass(ctx.df).run()
    ctx.my_output = result
    return result

MODULE_REGISTRY['my_module'] = {
    'needs': ['df'],
    'provides': ['my_output'],
    'run': _run_my_module,
    'description': '我的新模块',
}
```

**合并分支时必须检查：** 新增的每个 .py 文件是否都接入了管线。

**验证命令：** `python check_orphans.py` — 应输出 "0 orphaned modules"

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
