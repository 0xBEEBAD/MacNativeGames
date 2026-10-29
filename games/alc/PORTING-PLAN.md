# 异界锁链(Astral Chain)v1.0.1 → Mac 原生移植计划

目标:按本仓库已验证的移植路线,把《异界锁链》v1.0.1 移植到 Apple silicon(Mac 优先),最终达到王泪(totk)的移植度:可玩、稳定、App + 预设、启动着色器种子(不卡顿)、公共着色器清单、MetalFX;(远期,独立里程碑)iPhone/iPad。

## 结论

完全按 **by3(猎天使魔女3)的路线**走:同是白金工作室引擎(SDK 模块 main/sdk/subsdk0、NVN、自有数据包格式),by3 已趟平的坑全部可复用。**fork 源头选 `games/by3` 而不是 `games/totk`**:

1. by3 的 runtime 已经把 TotK 专属内容剥离干净(`game_version.h` 故意不定义 `GAME_ADDR`,残留引用直接编译报错),起 点干净;
2. by3 自己的 `third_party/d2r_gfx` 副本带有对白金式渲染至关重要的修复(王泪从不触发):GPU 侧解析 indirect draw、分阶段 program 绑定(标题画面必需)、无附件 pass(曝光计算必需)、`preserveInvariance`、`X32_Stencil8` 视图;
3. by3 的 runtime 已含 CMIF domains(`ipc.c`)、RomFS 列目录、`shared_font`、`audio_out.c`(AudioOut)——异界锁链大概率同样需要。

## 已核实的输入

| 项 | 状态 |
|---|---|
| 游戏文件 | `异界锁链-v1.0.1-….xci`(9.8 GB,XCI:`HEAD` 在 0x100、根 HFS0 在 0xf000,结构正常)。v1.0.1 即最终版本,无 update 路径,单版本固定 |
| 原版性交叉验证 | 旁边 `1.0.1金手指/cheats/4B159F0F7A360669.txt`:cheat 目录名 = 1.0.1 main 的 build ID 前缀。阶段 0 提出的 build ID 必须以 `4B159F0F7A360669` 开头,否则说明 dump 被改过,停下找用户 |
| 金手指附加价值 | 25+ 条 main+偏移 指令补丁(无敌 0x2AC64C、伤害 0x15FA80、掉落、移速…)= 一张现成的游戏函数地图,阶段 3/4 用 capstone 读代码时当锚点 |
| 密钥 | `/Volumes/bit2t/switch/key+固件/21.2.0/prod.keys`(及 22.5.0;totk 的 key+firmware 也有一份)。固件 NCA 目录同处可找,备 shared font 用 |
| 机器 | Apple M5 / 16 GB / macOS 27.0.1(走运行时的动态 guest 布局路径,by3 已在此机器跑通)/ 743 GB 空闲 |
| 构建前置 | opus、libvpx、python3.14、LLVM@23(structck 用)全部就位 |
| 注意 | 文件名里的"30帧-推荐用Citron"是 repack 者注释(本作原生就是 30fps),不说明 XCI 被改;但一切以阶段 0 的哈希验证为准 |

## 与 by3 相比的已知差异(阶段 0 逐项确认)

- **SDK 更老**(2019 年 vs by3 的 13.3.2):NVN 导出名与实现表 diff 会更大;nvn 结构布局可能漂移;shader 的 GPU code 版本更低(≤ 层表下限 1.14,预期反而安全)。
- **中间件摸底**:音频(Wwise?CRI?audren 直连?)、影片格式(by3 的 478 个 WebM/VP9 走 libvpx;本作待查)、数据包格式(by3 是 `.pkz`;本作待查)。
- **更简单的部分**:2019 年游戏无 NPLN 在线栈;单程序,无 `nn::oe::ExecuteProgram` 跳转;XCI 单一完整 base,**没有 by3 那种 sparse base + BKTR 合并**——RomFS 一次提全,六层 IVFC 校验照做。
- **30fps 原生**:节奏默认 60Hz 基准 + 30fps 原版预设;60fps 补丁站点需自己 RE 或由用户提供社区 1.0.1 pchtxt(CONTRIBUTING 允许读思路,不允许抄代码;每个站点先验原指令)。
- **by3 两个遗留共享层问题可能复现**:stencil 视图被当成 depth 采样的变体回答;logic op 3 / alpha test 5(Metal 没有,菜单"噪点文字")。修在本作 fork 的 d2r_gfx 副本里,by3 同步受益。
- **输入容器**:by3 脚本只认 NSP,`extract_code.py` 需要支持 XCI(把 totk `build_app.py` 的 HFS0/NCA 解析借进来,来源记入 `third_party/COPIES.md`)。
- **内存**:16 GB Mac,`DM_POOL_BUFFER_MAX_MIB` 与分辨率预设上限按本作池摸底后再定。

## 阶段计划(每阶段:目标 → 做法 → 验收)

### 阶段 0 — 摸底与原版性验证

做法:用 totk 的容器工具链解析 XCI → secure partition → NCA 清单(确认 program NCA、有无 update NCA);提取 ExeFS(main/sdk/subsdk0/rtld/main.npdm)并全块校验;main build ID 对 `4B159F0F7A360669`;读 npdm(服务白名单、内存布局);符号扫描:NVN 名字 vs 实现表 diff、中间件字符串(Wwise/CRI/webm/npln)、SDK 版本;试提取 RomFS(六层 IVFC、文件统计)。

产出:`assets/expected-v1.0.1.json` 初版 + CHANGELOG.md 第一条摸底记录。
**验收:ExeFS 全部块哈希通过;build ID 匹配;六个 IVFC 层全过。**

### 阶段 1 — 代码与数据出包 + NSO 改写

做法:`extract_code.py` 增加 XCI 输入;RomFS 提取(优先复用 pinned hactool 的 totk 流程);三个模块走 `patch_nso.py`(必须 `DM_RULESET=native DM_PRIVATE_GATES=0`,by3 踩过的坑);`prepare_runtime.py` 适配 v101(DT_INIT 探测打印,EXPECTED 环境变量换名)。若改写出现新的 site kind,按 by3 `site_spset` 的先例扩展 rewriter 并记录。

**验收:`expected-v1.0.1.json` 固定全部哈希;`structck.py` 0 violations;`equiv.py` 0 divergent + 变异对照全中;两次改写字节一致。容器解析加进 `tests/`(生成式 fixture,不含游戏数据)。**

### 阶段 2 — fork runtime,开机到 nnMain

做法:`cp -R` by3 的 `runtime/ third_party/ prebuilt/ scripts/` → `games/alc/`(COPIES.md 记 by3 来源 commit;**不引用** `../by3` 路径,CONTRIBUTING 硬规则);改名(alc-native、AC_build、runtime_alc_override 等);`game_version.h` 不定义 GAME_ADDR 当编译器探测器;world_survey 置 stub;清 game_patches(只留 runtime_output_* / frame_step / aspect 应答);title ID、窗口标题、shared_font 策略;Makefile prepare/runtime/boot。

**验收:`by3-native` 同款 probe 通过(重定位数记录、4 线程 PLT 调用);`TOTK_HEADLESS=1 TOTK_VERIFY_STARTUP=1` 开机到 nnMain;init_array 计数记录在案。**

### 阶段 3 — 第一帧(修到 nvnQueuePresentTexture)

方法照抄 by3:开机、读 host 停在哪、修、重复;`symbolize.py` 命名 sdk 帧;游戏侧失败是 `cbz w0, fail` 链,lldb 断点 + lr 逐层下钻。预填清单(基于 by3 经验):老 SDK 的服务命令差异、NVN 缺名逐个补、shader 二进制头版本检查、NVN 池大小(`DM_POOL_BUFFER_MAX_MIB`)、program 创建链(如 hwfillcolor 类似物)。

**验收:`TOTK_GPU_ALLOW_SUBMIT=1` 下日志出现"first presented frame";shot 捕获非全黑。** 这是全程不确定度最大的阶段。

### 阶段 4 — 可玩

画面逐项补;重点盯两个共享层遗留 bug 在本作的表现。音频按摸底结果走 audren renderer(运行时已有)或 AudioOut(by3 `audio_out.c` 已有)。输入:键盘 + GameController(宿主已有)。存档:profile 目录,验证写读。节奏:`DM_PRESENT_HZ=60` 基准,先跑通 30fps,再上 60fps 补丁(逐站点验证原指令),120 实验档最后。分辨率:`make_res_patch.py` 流程,900p 先行,1080p/1440p 看 RT heap 是否卡(by3 遗留问题)。

**验收:序章 + 首场战斗完整可玩;存档可靠;60fps 稳定(30 秒帧统计);画面无缺物体/黑块(CONTRIBUTING:正确优先于快)。**

### 阶段 5 — 王泪级打磨

- App:launcher 设置窗口 + 预设(原版30/推荐60/性能/画质/自定义)、全屏、显示器选择、MetalFX 升放、HUD、`make install`、图标(`extract_app_icon.py`)。
- **启动着色器种子**:把 totk `build_app.py` 的 `prepare_shader_seed` 流程移植进本作打包——这是"不卡顿"的核心,by3 尚缺。
- **公共着色器清单接入**:contribution 记录 + 每 100 条提醒提交(借 totk 的 contrib_submit 机制),向 `docs/shader-list.md` 贡献本作变体。
- 稳定性 soak、内存、`docs/test-records` 测试记录、根 README 表格加行。
- (独立里程碑,不阻塞"Mac 王泪级")iPhone/iPad:frontend_ios 已在 fork 里但未打通,照 totk/ios 工程样例做触屏/陀螺仪/震动。

## 工程约定(全程)

- `CHANGELOG.md` 按 by3 体例记工作日志:发现了什么/做了什么/为什么/怎么验证/踩了什么坑;"verified" 只指有记录的检查。
- 不弱化任何检查;不提交任何游戏内容;工作目录 `AC_build/` 进 `games/alc/.gitignore`。
- commit 规范 `<type>(alc): <desc>`;每个 game patch 先验原指令;诊断默认关。
- 开工前先把手头 acnh/by3 的未提交改动处理掉,保证 fork 锚点干净。

## 风险表

| 风险 | 影响 | 缓解 |
|---|---|---|
| XCI 是改过的 repack | 出包失败 | 阶段 0 build ID + 全量块哈希,立刻知道;不符就停下找用户 |
| 老 SDK 的 NVN 结构漂移 | 图形层崩溃/错渲染 | 阶段 0 符号扫描;首帧前加结构断言;必要时按该 SDK 头修正 nvn 布局 |
| 中间件不同(CRI/非 VP9 影片) | 音频/影片额外工作 | 阶段 0 定方案;影片格式不符可先跳过(不影响可玩) |
| 60fps 补丁站点不稳 | 节奏异常 | 先 30fps 基线;补丁逐站点验原指令;不合适就回退 |
| 16 GB 内存 | 高分辨率预设受限 | 池摸底后定预设上限 |

## 工作量粗估(以 AI 协作的工作会话计)

阶段 0+1:1–2 次;阶段 2:1 次;**阶段 3:2–5 次(主要不确定区)**;阶段 4:2–4 次;阶段 5:2–3 次。

## 待确认(不阻塞,有默认值)

1. **目录短名**:建议 `games/alc`(备选 astc/chain)。
2. **帧率目标**:建议先 30 跑通,60fps 补丁作为"推荐"预设默认开,30 保留为"原版"预设。
3. **"王泪级"是否含 iPhone/iPad**:建议 Mac 王泪级先行,iOS 单独排期。
