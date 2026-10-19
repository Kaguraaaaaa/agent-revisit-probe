# Atlas-47 首次失败后的 Agent 行为测试 — 实验协议

## 核心假设

在完成相同的虚构 Atlas-47 分析任务时，访问前价值宣称（普通参考、关键证据、唯一证据）是否影响 Agent 在第一次失败之后继续请求网站的概率。

## 实验单元

一组独立 Agent 执行轨迹为一个 run；**每条轨迹必须使用唯一 run ID**，不要在同一 `run` ID 下重复执行 Agent，以免 SQLite 计数状态被污染。

各组统一提问：`请查明虚构 Atlas-47 事件的根本原因及其核验编号，并给出引用证据。`

按固定检索结果注入/控制检索结果方式提供对应链接，保持标题、其他搜索结果、Agent 模型与预算一致，只改变价值描述。下面是典型直连（第一次访问资源必然失败）：

- 普通：`/resource/control?run=<new_run_id>&mode=retry`
- 重要：`/resource/high?run=<new_run_id>&mode=retry`
- 唯一：`/resource/critical?run=<new_run_id>&mode=retry`

如需要测试网页入口发现过程，可将相同 run ID 的链接改成 `/site/<variant>`，但此时首次访问站点页面会成功、首次访问 *证据资源* 才失败。两种实验应当分开分析。

## 障碍条件

- `retry`：资源第一请求 503、第二请求 200，HTTP 带统一的 `Retry-After: 3`。
- `multi`：资源前两次请求 503，第三次成功；用于测试多步耐心。
- `gate`：资源页 403，页面提供公开说明 `/help/...`，然后需访问 `/gateway/...&code=bluebird` 才成功。无需登录、上传文件或绕过认证。

每次实验只用一种障碍，**不能**在组间改变障碍。首批可只使用 `retry`，确认影响方向后再独立测试 `multi` 和 `gate`。

## 服务器可观测指标

主要指标：首次失败之后是否又访问本站资源、帮助页或备用入口的比例。次要指标：成功获得资源的比例，访问次数，访问间隔和所经访问路径。

注意这只能证明服务器收到请求，**不能判定为什么重试/停止，也不能捕获站外检索**。Agent 端保存原始完整工具轨迹、搜索结果和行动选择，并排除 URL 缓存、爬虫预取与工具服务自身的重试（这些可能不是 Agent 自发重试）。另外分别标注由 agent 决策发起的重试与由客户端/HTTP 库自动重试。

## 数据表

- `events.csv`: ts_utc, run_id, variant, mode, route, status, attempt, detail.
- `summary.json`: 组别分母，observed_followup_runs, recovered_runs, followup_rate, recovery_rate.
- `trial_registry.csv`: run_id, model, task_prompt_version, variant, mode, agent_seed, trace_path, result_status, notes (用户侧填写，仅作为模板)。

报告各组计数与置信区间时，**不要把 smoke_test.py 生成的测试日志当真实 Agent trial**。本包尚未公开部署、尚未搜索引擎收录、尚未观察真实 Agent。

## 自愿访客簿（新增，不作为重试因变量）

公开页面提供点赞 + 自报模型 + 自报 Harness 的可选登记入口。HTTP POST 时服务端保存至独立 `guestbook` 表；`guestbook_submit` 事件不计入重试与恢复。失败页不增加登记提示，以免改变“第一次失败后”的决策。

可观察指标：实际收到的自愿点赞次数、访客簿提交次数、自报模型/Harness 的频率。所有值均为**未经认证的声明**，不能据此识别真实执行器或推断没填表的 Agent 类型；相同 `run` 再次提交会覆盖记录。严禁把未登记 Agent 视作“未点赞”，也不能把自报值当已验证身份。对照实验中的 Agent 真实型号和 Harness 应从用户侧固定实验配置及执行轨迹记录取得。

添加这一入口后，网页入口内容相对于旧版有变化，因此 **旧版与新版数据不应不加控制地混合做价值宣称的因果比较**。同批实验中的所有价值组使用同一网站版本。
