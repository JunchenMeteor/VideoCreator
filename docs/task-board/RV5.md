# RV5 清理修复与独立复测评审

永久独立评审owner；当前准备，待I5固定正式交接后分派。只读实现/测试/标准与普通可读证据，写docs/reviews及自身Review；不运行测试或修源码，费用/key/部署0。

输入固定：ADR0005、RV4-P01/P02、T7Handoff与38普通副本、I5最终Handoff及新三源、T8/T9正式终态（未交部分待定，不能继承owner绿）。保留T7实际15pass/Node0但GBK包装1，以及P01真实Python反例/P02隔离源回调反例红。

源码核P01身份查询失败/未获root身份/快速退出时verification保持诚实，未知目标不可盲force；P02同步/异步API reject时前端一路仍执行并独立汇总失败，非零真实出口不被吞掉。检查正常关闭、startup失败、marker/actualexit/port/owned组合和兄弟保护语义；有限PID创建快照及taskkill TOCTOU限制不消失。

证据按来源分列：owner自查、T独立真实Node→Python、隔离回调模拟、真正前端自有进程清理、完整DevRuntime信号/UI、原生桌面/安装/Worker。只支持实际固定范围；不以模拟调用计数关闭OS清理。T8只评startup标签窄补，不能倒改旧T6身份/结果；新结构测试绑定须保持同义原失败期望。

静态阶段可先FINAL释放，再收到T9正式证据另补批；不因缺后续证据长期等待。任何关闭必须列精确源hash、收据/命令真实退出和未测项；尚缺的完整Vite/父崩溃/三OS/自主作品/Gateway/商业均保留。技术Gate、R1、R2和安装验收不由本局部评审签字。
