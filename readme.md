# CoreCI: RDSCore的CI

## 里程碑
- [X] 执行AutoTest中(不需要仿真rbk的) && (rdscore) && (m0标记的)测试用例并生成报告
- [ ] 可以安装的TestRunner
- [ ] 接入coding.net
- [ ] 容器化TestRunner
- [ ] 执行使用仿真rbk的测试用例

## 结构
1. TestRunner：执行测试任务
2. Dispatcher：分发测试任务给TestRunner，维护测试报告

### TestRunnerStatus

- Running
- Idle
- Unavailable

### JobStatus

- Running
- Done
- Discarded

### 发起测试的流程
1. 在网页上上传版本
2. 选择版本，提交测试任务
3. Dispatcher收到测试任务后，选择合适的TestRunner，判断标准：Idle且操作系统匹配
4. Dispatcher发送版本给TestRunner
5. Dispatcher发送任务给TestRunner
6. TestRunner执行任务