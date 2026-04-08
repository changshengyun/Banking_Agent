import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'banking_api.dart';

const String _invalidInputMessage = '无效输入，请按照要求输入';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  MyApp({
    super.key,
    BankingApiClient? apiClient,
  }) : apiClient = apiClient ?? HttpBankingApiClient();

  final BankingApiClient apiClient;

  @override
  Widget build(BuildContext context) {
    const Color primaryRed = Color(0xFFDB0011);
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '银行 AI 智能体演示',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primaryRed,
          primary: primaryRed,
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF3F5F8),
      ),
      home: BankHomePage(apiClient: apiClient),
    );
  }
}

class BankHomePage extends StatefulWidget {
  const BankHomePage({super.key, required this.apiClient});

  final BankingApiClient apiClient;

  @override
  State<BankHomePage> createState() => _BankHomePageState();
}

class _BankHomePageState extends State<BankHomePage> {
  final List<_UiChatMessage> _chatMessages = <_UiChatMessage>[
    const _UiChatMessage(
      text: '你好，我是演示版银行 AI 助手。你可以让我查余额、查账单，或解释风控原因。',
      isUser: false,
    ),
  ];

  static const Map<String, Offset> _cityCoordinates = <String, Offset>{
    '上海': Offset(121.4737, 31.2304),
    '北京': Offset(116.4074, 39.9042),
    '西安': Offset(108.9398, 34.3416),
  };

  DashboardData? _dashboard;
  String? _errorMessage;
  bool _loading = true;
  bool _hideAssets = false;
  int _currentTab = 0;
  String _currentCity = '上海';
  String _deviceId = '演示设备-001';
  final String _sessionId = DateTime.now().millisecondsSinceEpoch.toString();

  @override
  void initState() {
    super.initState();
    unawaited(_loadDashboard());
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    try {
      final DashboardData dashboard = await widget.apiClient.fetchDashboard();
      if (!mounted) return;
      setState(() {
        _dashboard = dashboard;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = error.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _errorMessage = '无法连接后端服务，请先启动 FastAPI。';
        _loading = false;
      });
    }
  }

  ClientContextData _context({
    required String city,
    required String page,
    required String action,
    required String summary,
    int? inputPauseCount,
    int? inputDurationMs,
    Map<String, dynamic> extraSignals = const <String, dynamic>{},
  }) {
    final Offset point = _cityCoordinates[city] ?? const Offset(121.4737, 31.2304);
    return ClientContextData(
      sessionId: _sessionId,
      deviceId: _deviceId,
      platform: 'android-demo',
      currentCity: city,
      lat: point.dy,
      lng: point.dx,
      recentPage: page,
      lastAction: action,
      semanticSummary: summary,
      inputPauseCount: inputPauseCount,
      inputDurationMs: inputDurationMs,
      extraSignals: extraSignals,
    );
  }

  String _money(double value) =>
      _hideAssets ? '****' : '¥${value.toStringAsFixed(2)}';

  String _riskLevelLabel(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
        return '高风险';
      case 'medium':
        return '中风险';
      case 'low':
        return '低风险';
      default:
        return '风险未知';
    }
  }

  void _showSnack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _cancelPendingTransfer(String confirmationToken) async {
    try {
      final TransferCancelResult result =
          await widget.apiClient.cancelTransfer(confirmationToken);
      _showSnack(result.assistantMessage);
    } on ApiException catch (error) {
      _showSnack(error.message);
    } catch (_) {
      _showSnack('取消交易失败，请稍后重试');
    }
  }

  Future<void> _openBillSheet() async {
    try {
      final TransactionsData transactions =
          await widget.apiClient.fetchTransactions(limit: 20);
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        builder: (BuildContext context) => SizedBox(
          height: MediaQuery.of(context).size.height * 0.76,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: Column(
              children: <Widget>[
                const _SheetHandle(),
                const SizedBox(height: 10),
                Row(
                  children: <Widget>[
                    const Text(
                      '账单明细',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                    ),
                    const Spacer(),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                if (transactions.spendingSummary.isNotEmpty) ...<Widget>[
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: transactions.spendingSummary
                          .map(
                            (SpendingSummaryItem item) => Chip(
                              label: Text(
                                '${item.category} ¥${item.totalAmount.toStringAsFixed(0)}',
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                Expanded(
                  child: ListView.separated(
                    itemCount: transactions.items.length,
                    separatorBuilder: (_, _) => const Divider(height: 1),
                    itemBuilder: (BuildContext context, int index) {
                      final TransactionRecord record = transactions.items[index];
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(record.title),
                        subtitle: Text('${record.subtitle} · ${record.city}'),
                        trailing: Text(
                          '${record.isIncome ? '+' : '-'}¥${record.amount.toStringAsFixed(2)}',
                          style: TextStyle(
                            color: record.isIncome
                                ? const Color(0xFF1E7A3F)
                                : Colors.black87,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    } on ApiException catch (error) {
      _showSnack(error.message);
    } catch (_) {
      _showSnack('账单加载失败，请稍后重试');
    }
  }

  Future<void> _openTransferSheet({
    String payeePreset = '',
    String amountPreset = '',
    String cityPreset = '上海',
  }) async {
    final TextEditingController payeeController = TextEditingController(text: payeePreset);
    final TextEditingController amountController = TextEditingController(text: amountPreset);
    final TextEditingController deviceController = TextEditingController(text: _deviceId);
    final Stopwatch inputStopwatch = Stopwatch()..start();
    int inputPauseCount = 0;
    DateTime? lastInputAt;
    const Duration pauseThreshold = Duration(milliseconds: 1200);
    void recordInputTick() {
      final DateTime now = DateTime.now();
      if (lastInputAt != null && now.difference(lastInputAt!) > pauseThreshold) {
        inputPauseCount += 1;
      }
      lastInputAt = now;
    }

    String selectedCity = cityPreset;
    bool busy = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (BuildContext context) => StatefulBuilder(
        builder: (BuildContext context, StateSetter setModalState) => SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            16,
            16,
            16,
            MediaQuery.of(context).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const _SheetHandle(),
              const SizedBox(height: 12),
              const Text('发起转账', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              TextField(
                controller: payeeController,
                onChanged: (_) => recordInputTick(),
                decoration: const InputDecoration(labelText: '收款人', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: amountController,
                keyboardType: TextInputType.number,
                onChanged: (_) => recordInputTick(),
                decoration: const InputDecoration(labelText: '金额（元）', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: selectedCity,
                items: _cityCoordinates.keys
                    .map((String city) => DropdownMenuItem<String>(value: city, child: Text(city)))
                    .toList(),
                onChanged: (String? value) {
                  if (value != null) {
                    setModalState(() => selectedCity = value);
                  }
                },
                decoration: const InputDecoration(labelText: '当前城市', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: deviceController,
                onChanged: (_) => recordInputTick(),
                decoration: const InputDecoration(labelText: '设备标识', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final double? amount = double.tryParse(amountController.text.trim());
                          final String payee = payeeController.text.trim();
                          final String deviceId = deviceController.text.trim();
                          if (inputStopwatch.isRunning) {
                            recordInputTick();
                          }
                          final int inputDurationMs = inputStopwatch.elapsed.inMilliseconds;
                          if (amount == null || amount <= 0 || payee.isEmpty || deviceId.isEmpty) {
                            _showSnack(_invalidInputMessage);
                            return;
                          }
                          setModalState(() => busy = true);
                          setState(() {
                            _currentCity = selectedCity;
                            _deviceId = deviceId;
                          });
                          try {
                            final TransferPrecheckResult precheck =
                                await widget.apiClient.precheckTransfer(
                              payeeName: payee,
                              amount: amount,
                              context: _context(
                                city: selectedCity,
                                page: 'home',
                                action: 'tap_transfer_precheck',
                                summary: '用户从首页发起转账，等待智能体预检。',
                                inputPauseCount: inputPauseCount,
                                inputDurationMs: inputDurationMs,
                                extraSignals: <String, dynamic>{
                                  'payee_length': payee.length,
                                  'amount_text_length': amountController.text.trim().length,
                                  'pause_threshold_ms': pauseThreshold.inMilliseconds,
                                },
                              ),
                            );
                            if (context.mounted) Navigator.pop(context);
                            if (!mounted) return;
                            _showSnack(precheck.assistantMessage);
                            await _handlePrecheck(precheck);
                          } on ApiException catch (error) {
                            if (context.mounted) setModalState(() => busy = false);
                            _showSnack(error.message);
                          } catch (_) {
                            if (context.mounted) setModalState(() => busy = false);
                            _showSnack('转账预检失败，请检查后端服务');
                          }
                        },
                  child: Text(busy ? '检测中...' : '提交预检'),
                ),
              ),
            ],
          ),
        ),
      ),
    );

    inputStopwatch.stop();
    await Future<void>.delayed(const Duration(milliseconds: 250));
    payeeController.dispose();
    amountController.dispose();
    deviceController.dispose();
  }

  Future<void> _handlePrecheck(TransferPrecheckResult result) async {
    final String decision = result.decision;
    if (decision == 'block') {
      await showDialog<bool>(
        context: context,
        builder: (BuildContext context) => AlertDialog(
          title: Text('转账被拦截 · ${_riskLevelLabel(result.riskLevel)}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(result.assistantMessage.isEmpty ? '该笔转账存在高风险，请联系客服确认。' : result.assistantMessage),
              const SizedBox(height: 12),
              _XaiExplainPanel(explainPack: result.explainPack),
              const SizedBox(height: 12),
              ...result.reasons.map((String reason) => Text('• $reason')),
            ],
          ),
          actions: <Widget>[
            FilledButton.tonal(onPressed: () => Navigator.pop(context, true), child: const Text('知道了')),
          ],
        ),
      );
      return;
    }

    if (decision == 'interrogate') {
      final _SecondaryReplyOutcome outcome = await _showSecondaryReplyDialog(result);
      if (!mounted) return;
      if (outcome.action == _SecondaryReplyAction.dismiss) return;
      if (outcome.action == _SecondaryReplyAction.cancelTransaction) {
        await _cancelPendingTransfer(result.confirmationToken);
        return;
      }

      final String userReply = outcome.reply!;
      try {
        final TransferSecondaryCheckResult secondary =
            await widget.apiClient.secondaryCheckTransfer(
          confirmationToken: result.confirmationToken,
          userReply: userReply,
          context: _context(
            city: _currentCity,
            page: 'transfer',
            action: 'secondary_check',
            summary: '用户在二次质询阶段提交解释。',
            extraSignals: <String, dynamic>{
              'reply_length': userReply.length,
            },
          ),
        );
        _showSnack(secondary.assistantMessage);
        if (secondary.secondaryDecision == 'block_secondary') {
          await _showSecondaryBlockedDialog(secondary);
          return;
        }
        if (secondary.secondaryDecision == 'interrogate') {
          await _showSecondaryInterrogateDialog(secondary);
          return;
        }
        if (secondary.secondaryDecision != 'pass_secondary') {
          _showSnack('当前转账未通过二次校验，无法继续确认');
          return;
        }
      } on ApiException catch (error) {
        _showSnack(error.message);
        return;
      } catch (_) {
        _showSnack('二次校验失败，请稍后重试');
        return;
      }
    }

    try {
      final TransferConfirmResult confirm =
          await widget.apiClient.confirmTransfer(result.confirmationToken);
      _showSnack(confirm.assistantMessage);
      await _loadDashboard();
    } on ApiException catch (error) {
      _showSnack(error.message);
    } catch (_) {
      _showSnack('模拟转账执行失败');
    }
  }

  Future<_SecondaryReplyOutcome> _showSecondaryReplyDialog(
    TransferPrecheckResult result,
  ) async {
    String replyDraft = '';
    final RiskClassificationData classification = result.riskClassification;
    final List<String> followUpQuestions =
        classification.followUpQuestions.isNotEmpty
        ? classification.followUpQuestions
        : const <String>[
            '请说明你与收款人的关系。',
            '请说明本次转账用途。',
            '请说明是否涉及验证码、安全账户或屏幕共享。',
          ];
    final List<String> replyExamples =
        classification.suggestedReplyExamples.isNotEmpty
        ? classification.suggestedReplyExamples
        : const <String>[
            '收款人是小b，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码或安全账户。',
          ];
    final _SecondaryReplyOutcome? outcome = await showDialog<_SecondaryReplyOutcome>(
      barrierDismissible: false,
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: Text('二次质询 · ${_riskLevelLabel(result.riskLevel)}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                classification.analysis.isNotEmpty
                    ? classification.analysis
                    : result.assistantMessage,
              ),
              const SizedBox(height: 12),
              _XaiExplainPanel(explainPack: result.explainPack),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8E8EA),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      '请说明以下内容',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...followUpQuestions.map(
                      (String question) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text('• $question'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                '回答样例',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              ...replyExamples.take(2).map(
                (String example) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text('示例：$example'),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                maxLines: 4,
                onChanged: (String value) {
                  replyDraft = value;
                },
                decoration: const InputDecoration(
                  labelText: '请输入说明',
                  hintText: '关系 + 用途 + 是否涉及验证码/安全账户/屏幕共享',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(
              context,
              const _SecondaryReplyOutcome.dismiss(),
            ),
            child: const Text('关闭'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(
              context,
              const _SecondaryReplyOutcome.cancelTransaction(),
            ),
            child: const Text('取消交易'),
          ),
          FilledButton(
            onPressed: () {
              final String text = replyDraft.trim();
              if (text.isEmpty) {
                _showSnack(_invalidInputMessage);
                return;
              }
              Navigator.pop(context, _SecondaryReplyOutcome.submit(text));
            },
            child: const Text('提交校验'),
          ),
        ],
      ),
    );
    return outcome ?? const _SecondaryReplyOutcome.dismiss();
  }

  Future<void> _showSecondaryBlockedDialog(
    TransferSecondaryCheckResult result,
  ) async {
    await showDialog<void>(
      barrierDismissible: false,
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('二次校验未通过'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(result.assistantMessage),
            const SizedBox(height: 12),
            _XaiExplainPanel(explainPack: result.explainPack),
            const SizedBox(height: 12),
            ...result.reasons.map((String reason) => Text('• $reason')),
          ],
        ),
        actions: <Widget>[
          FilledButton.tonal(
            onPressed: () => Navigator.pop(context),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  Future<void> _showSecondaryInterrogateDialog(
    TransferSecondaryCheckResult result,
  ) async {
    await showDialog<void>(
      barrierDismissible: false,
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('二次说明未通过'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(result.assistantMessage),
            const SizedBox(height: 12),
            _XaiExplainPanel(explainPack: result.explainPack),
            const SizedBox(height: 12),
            ...result.reasons.map((String reason) => Text('• $reason')),
          ],
        ),
        actions: <Widget>[
          FilledButton.tonal(
            onPressed: () => Navigator.pop(context),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  void _openAiSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (BuildContext context) => _AiChatSheet(
        messages: _chatMessages,
        apiClient: widget.apiClient,
        contextFactory: (String action, String summary) => _context(
          city: _currentCity,
          page: 'chat',
          action: action,
          summary: summary,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('银行 AI 智能体风控演示'),
        actions: <Widget>[
          IconButton(onPressed: () => unawaited(_loadDashboard()), icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: IndexedStack(
        index: _currentTab,
        children: <Widget>[
          _buildHome(),
          const _PlaceholderTab(title: '支付', hint: '当前重点展示转账风控与智能体对话能力。'),
          const _PlaceholderTab(title: '理财', hint: '理财推荐作为扩展功能预留。'),
          const _PlaceholderTab(title: '我的', hint: '这里可扩展设备、地点与用户画像信息。'),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openAiSheet,
        backgroundColor: const Color(0xFFDB0011),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.smart_toy_outlined),
        label: const Text('AI 助手'),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentTab,
        onDestinationSelected: (int index) => setState(() => _currentTab = index),
        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.home_rounded), label: '首页'),
          NavigationDestination(icon: Icon(Icons.qr_code_2_rounded), label: '支付'),
          NavigationDestination(icon: Icon(Icons.trending_up_rounded), label: '理财'),
          NavigationDestination(icon: Icon(Icons.person_rounded), label: '我的'),
        ],
      ),
    );
  }

  Widget _buildHome() {
    if (_loading && _dashboard == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null && _dashboard == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.cloud_off_rounded, size: 56, color: Color(0xFFDB0011)),
              const SizedBox(height: 12),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: () => unawaited(_loadDashboard()), child: const Text('重试')),
            ],
          ),
        ),
      );
    }

    final DashboardData dashboard = _dashboard!;
    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 18),
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: const LinearGradient(
                colors: <Color>[Color(0xFF2B64D8), Color(0xFF163FA8), Color(0xFF0F2D79)],
              ),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Row(children: <Widget>[
                Text('${dashboard.userName} 的演示账户', style: const TextStyle(color: Colors.white70)),
                const Spacer(),
                IconButton(
                  onPressed: () => setState(() => _hideAssets = !_hideAssets),
                  icon: Icon(_hideAssets ? Icons.visibility_off_rounded : Icons.visibility_rounded, color: Colors.white),
                ),
              ]),
              const Text('总资产', style: TextStyle(color: Colors.white, fontSize: 16)),
              const SizedBox(height: 6),
              Text(
                _money(dashboard.totalAssets),
                style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                '活期 ${_money(dashboard.cashBalance)}    理财 ${_money(dashboard.wealthBalance)}',
                style: const TextStyle(color: Colors.white70),
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(dashboard.demoTip, style: const TextStyle(color: Colors.white)),
              ),
            ]),
          ),
          const SizedBox(height: 16),
          Row(children: <Widget>[
            const Text('演示入口', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const Spacer(),
            Chip(label: Text('当前城市 $_currentCity')),
          ]),
          const SizedBox(height: 10),
          GridView.count(
            shrinkWrap: true,
            crossAxisCount: 4,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            physics: const NeverScrollableScrollPhysics(),
            children: <Widget>[
              _QuickButton(label: '转账', icon: Icons.swap_horiz_rounded, onTap: () => unawaited(_openTransferSheet())),
              _QuickButton(
                label: '风险演示',
                icon: Icons.shield_rounded,
                accent: true,
                onTap: () => unawaited(_openTransferSheet(payeePreset: '小c', amountPreset: '8000', cityPreset: '北京')),
              ),
              _QuickButton(
                label: '账单',
                icon: Icons.receipt_long_rounded,
                onTap: () => unawaited(_openBillSheet()),
              ),
              _QuickButton(label: 'AI 助手', icon: Icons.auto_awesome_rounded, accent: true, onTap: _openAiSheet),
            ],
          ),
        ],
      ),
    );
  }
}

class _AiChatSheet extends StatefulWidget {
  const _AiChatSheet({
    required this.messages,
    required this.apiClient,
    required this.contextFactory,
  });

  final List<_UiChatMessage> messages;
  final BankingApiClient apiClient;
  final ClientContextData Function(String action, String summary) contextFactory;

  @override
  State<_AiChatSheet> createState() => _AiChatSheetState();
}

class _AiChatSheetState extends State<_AiChatSheet> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _sending = false;

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String text = _inputController.text.trim();
    if (_sending) return;
    if (text.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text(_invalidInputMessage)));
      return;
    }
    setState(() {
      _sending = true;
      widget.messages.add(_UiChatMessage(text: text, isUser: true));
    });
    _inputController.clear();
    try {
      final ChatReply reply = await widget.apiClient.chat(
        messages: widget.messages
            .map((message) => ChatTurn(role: message.isUser ? 'user' : 'assistant', content: message.text))
            .toList(),
        context: widget.contextFactory('send_chat_message', '用户在聊天窗口咨询余额、账单或风控原因。'),
      );
      if (!mounted) return;
      setState(() {
        widget.messages.add(
          _UiChatMessage(
            text: reply.assistantMessage,
            isUser: false,
            toolSummary: reply.usedTools
                .map((ToolUsageItem item) => item.summary.isNotEmpty ? item.summary : item.name)
                .join('；'),
          ),
        );
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        widget.messages.add(_UiChatMessage(text: '请求失败：$error', isUser: false));
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.78,
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 12, 16, MediaQuery.of(context).viewInsets.bottom + 12),
        child: Column(children: <Widget>[
          const _SheetHandle(),
          const SizedBox(height: 10),
          Row(children: <Widget>[
            const Text('AI 助手', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const Spacer(),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: widget.messages.length + (_sending ? 1 : 0),
              itemBuilder: (BuildContext context, int index) {
                if (_sending && index == widget.messages.length) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Text('正在调用智能体与工具...'),
                  );
                }
                final _UiChatMessage message = widget.messages[index];
                return Align(
                  alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: GestureDetector(
                    onLongPress: () => Clipboard.setData(ClipboardData(text: message.text)),
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.all(12),
                      constraints: const BoxConstraints(maxWidth: 310),
                      decoration: BoxDecoration(
                        color: message.isUser ? const Color(0x1FDB0011) : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: message.isUser ? const Color(0x66DB0011) : const Color(0xFFE6E6E6)),
                      ),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        SelectableText(message.text),
                        if (message.toolSummary != null && message.toolSummary!.isNotEmpty) ...<Widget>[
                          const SizedBox(height: 8),
                          Text('调用工具：${message.toolSummary!}', style: const TextStyle(fontSize: 12)),
                        ],
                      ]),
                    ),
                  ),
                );
              },
            ),
          ),
          Row(children: <Widget>[
            Expanded(
              child: TextField(
                controller: _inputController,
                enabled: !_sending,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => unawaited(_send()),
                decoration: InputDecoration(
                  hintText: '例如：帮我查余额 / 为什么触发风控？',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
            ),
            const SizedBox(width: 10),
            FloatingActionButton.small(
              onPressed: _sending ? null : () => unawaited(_send()),
              backgroundColor: const Color(0xFFDB0011),
              foregroundColor: Colors.white,
              child: const Icon(Icons.send_rounded),
            ),
          ]),
        ]),
      ),
    );
  }
}

class _QuickButton extends StatelessWidget {
  const _QuickButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.accent = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
          Icon(icon, color: accent ? const Color(0xFFDB0011) : const Color(0xFF2B64D8)),
          const SizedBox(height: 6),
          Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      ),
    );
  }
}

enum _SecondaryReplyAction {
  dismiss,
  cancelTransaction,
  submit,
}

class _SecondaryReplyOutcome {
  const _SecondaryReplyOutcome._(this.action, this.reply);

  const _SecondaryReplyOutcome.dismiss()
    : this._(_SecondaryReplyAction.dismiss, null);

  const _SecondaryReplyOutcome.cancelTransaction()
    : this._(_SecondaryReplyAction.cancelTransaction, null);

  const _SecondaryReplyOutcome.submit(String reply)
    : this._(_SecondaryReplyAction.submit, reply);

  final _SecondaryReplyAction action;
  final String? reply;
}

class _PlaceholderTab extends StatelessWidget {
  const _PlaceholderTab({required this.title, required this.hint});

  final String title;
  final String hint;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
          const Icon(Icons.account_balance_wallet_rounded, size: 56, color: Color(0xFFDB0011)),
          const SizedBox(height: 10),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 24)),
          const SizedBox(height: 8),
          Text(hint, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54)),
        ]),
      ),
    );
  }
}

class _SheetHandle extends StatelessWidget {
  const _SheetHandle();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 4,
      decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(100)),
    );
  }
}

class _XaiExplainPanel extends StatelessWidget {
  const _XaiExplainPanel({required this.explainPack});

  final ExplainPackData explainPack;

  Color _riskColor(String level) {
    switch (level.toLowerCase()) {
      case 'high':
        return const Color(0xFFB3261E);
      case 'low':
        return const Color(0xFF1E7A3F);
      default:
        return const Color(0xFF8A5A00);
    }
  }

  String _riskLabel(String level) {
    switch (level.toLowerCase()) {
      case 'high':
        return '高风险';
      case 'low':
        return '低风险';
      default:
        return '中风险';
    }
  }

  String _score(double value) => (value * 100).toStringAsFixed(0);

  @override
  Widget build(BuildContext context) {
    final List<ExplainNodeData> nodes = explainPack.nodes;
    final RiskScoreBreakdownData score = explainPack.scoreBreakdown;
    if (explainPack.headline.isEmpty && nodes.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F9FC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'XAI 风险解释',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            explainPack.headline,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (explainPack.recommendedAction.isNotEmpty) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              '建议动作：${explainPack.recommendedAction}',
              style: const TextStyle(fontSize: 12, color: Colors.black87),
            ),
          ],
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              Chip(label: Text('静态 S ${_score(score.flagS)}')),
              Chip(label: Text('行为 B ${_score(score.gBehavior)}')),
              Chip(label: Text('语义 G ${_score(score.gDynamic)}')),
              Chip(label: Text('综合 F ${_score(score.finalRisk)}')),
            ],
          ),
          if (nodes.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            ...nodes.map(
              (ExplainNodeData node) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                      margin: const EdgeInsets.only(top: 3),
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: _riskColor(node.level),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            '${node.title} · ${_riskLabel(node.level)} · ${(node.score * 100).toStringAsFixed(0)}',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          if (node.summary.isNotEmpty)
                            Text(node.summary, style: const TextStyle(fontSize: 12)),
                          if (node.detail.isNotEmpty)
                            Text(
                              node.detail,
                              style: const TextStyle(fontSize: 12, color: Colors.black54),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _UiChatMessage {
  const _UiChatMessage({
    required this.text,
    required this.isUser,
    this.toolSummary,
  });

  final String text;
  final bool isUser;
  final String? toolSummary;
}
