import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'banking_api.dart';

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
      title: 'Banking AI Demo',
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
    '深圳': Offset(114.0579, 22.5431),
    '苏州': Offset(120.5853, 31.2989),
  };

  DashboardData? _dashboard;
  String? _errorMessage;
  bool _loading = true;
  bool _hideAssets = false;
  int _currentTab = 0;
  String _currentCity = '上海';
  String _deviceId = 'android-demo-001';
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
    );
  }

  String _money(double value) =>
      _hideAssets ? '****' : '¥${value.toStringAsFixed(2)}';

  void _showSnack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openTransferSheet({
    String payeePreset = '',
    String amountPreset = '',
    String cityPreset = '上海',
  }) async {
    final TextEditingController payeeController = TextEditingController(text: payeePreset);
    final TextEditingController amountController = TextEditingController(text: amountPreset);
    final TextEditingController deviceController = TextEditingController(text: _deviceId);
    String selectedCity = cityPreset;
    bool busy = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (BuildContext context) => StatefulBuilder(
        builder: (BuildContext context, StateSetter setModalState) => Padding(
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
                decoration: const InputDecoration(labelText: '收款人', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: amountController,
                keyboardType: TextInputType.number,
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
                decoration: const InputDecoration(labelText: '设备 ID', border: OutlineInputBorder()),
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
                          if (amount == null || amount <= 0 || payee.isEmpty || deviceId.isEmpty) {
                            _showSnack('请完整填写转账信息');
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
                                summary: '用户从首页发起转账，等待 Agent 预检。',
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

    payeeController.dispose();
    amountController.dispose();
    deviceController.dispose();
  }

  Future<void> _handlePrecheck(TransferPrecheckResult result) async {
    if (result.decision == 'review') {
      final bool confirmed = await showDialog<bool>(
            context: context,
            builder: (BuildContext context) => AlertDialog(
              title: Text('风控提醒 · ${result.riskLevel.toUpperCase()}'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(result.assistantMessage),
                  const SizedBox(height: 12),
                  ...result.reasons.map((String reason) => Text('• $reason')),
                ],
              ),
              actions: <Widget>[
                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')),
                FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('仍要继续')),
              ],
            ),
          ) ??
          false;
      if (!confirmed) return;
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
        title: const Text('银行 AI Agent 风控演示'),
        actions: <Widget>[
          IconButton(onPressed: () => unawaited(_loadDashboard()), icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: IndexedStack(
        index: _currentTab,
        children: <Widget>[
          _buildHome(),
          const _PlaceholderTab(title: '支付', hint: '当前重点展示转账风控与 Agent 对话能力。'),
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
                onTap: () => _showSnack('最近交易已展示在首页，下滑即可查看'),
              ),
              _QuickButton(label: 'AI 助手', icon: Icons.auto_awesome_rounded, accent: true, onTap: _openAiSheet),
            ],
          ),
          const SizedBox(height: 16),
          const Text('最近交易', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: dashboard.recentTransactions
                  .map((TransactionRecord record) => ListTile(
                        title: Text(record.title),
                        subtitle: Text('${record.subtitle} · ${record.city}'),
                        trailing: Text(
                          '${record.isIncome ? '+' : '-'}¥${record.amount.toStringAsFixed(2)}',
                          style: TextStyle(
                            color: record.isIncome ? const Color(0xFF1E7A3F) : Colors.black87,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ))
                  .toList(),
            ),
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
    if (text.isEmpty || _sending) return;
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
            toolSummary: reply.usedTools.map((ToolUsageItem item) => item.name).join(', '),
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
                    child: Text('正在调用 Agent 与工具...'),
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
                          Text('Tools: ${message.toolSummary!}', style: const TextStyle(fontSize: 12)),
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
