import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_base/banking_api.dart';
import 'package:flutter_base/main.dart';

void main() {
  testWidgets('renders dashboard demo content', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    expect(find.text('银行 AI Agent 风控演示'), findsOneWidget);
    expect(find.text('演示入口'), findsOneWidget);
    expect(find.text('风险演示'), findsOneWidget);
    expect(find.text('总资产'), findsOneWidget);
  });

  testWidgets('opens ai assistant sheet', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.smart_toy_outlined));
    await tester.pumpAndSettle();

    expect(find.text('AI 助手'), findsWidgets);
    expect(find.byType(TextField), findsOneWidget);
  });
}

class _FakeApiClient implements BankingApiClient {
  @override
  Future<ChatReply> chat({
    required List<ChatTurn> messages,
    required ClientContextData context,
  }) async {
    return const ChatReply(
      assistantMessage: '当前可用余额为 2500.00 元。',
      usedTools: <ToolUsageItem>[
        ToolUsageItem(name: 'get_account_summary', summary: 'mock'),
      ],
      suggestedActions: <SuggestedActionItem>[
        SuggestedActionItem(label: '发起转账', action: 'open_transfer'),
      ],
    );
  }

  @override
  Future<TransferConfirmResult> confirmTransfer(String confirmationToken) async {
    return TransferConfirmResult(
      success: true,
      assistantMessage: '转账已完成',
      cashBalance: 2000,
      wealthBalance: 18000,
      totalAssets: 20000,
      latestTransaction: TransactionRecord(
        id: 'txn-demo',
        title: '转账给 张三',
        subtitle: 'AI Agent 风控确认后执行',
        amount: 500,
        isIncome: false,
        category: 'transfer',
        city: '上海',
        createdAt: '2026-03-16T10:00:00',
        status: 'posted',
      ),
    );
  }

  @override
  Future<DashboardData> fetchDashboard() async {
    return DashboardData(
      userName: '谢小璞',
      cashBalance: 2500,
      wealthBalance: 18000,
      totalAssets: 20500,
      currency: 'CNY',
      recentTransactions: <TransactionRecord>[
        TransactionRecord(
          id: 'txn-1',
          title: '工资入账',
          subtitle: '公司薪酬',
          amount: 12000,
          isIncome: true,
          category: 'income',
          city: '上海',
          createdAt: '2026-03-14T09:00:00',
          status: 'posted',
        ),
      ],
      spendingSummary: const <SpendingSummaryItem>[
        SpendingSummaryItem(category: 'food', totalAmount: 86),
      ],
      demoTip: '演示模式已开启：异地、大额、首次收款人会触发 Agent 风控确认。',
    );
  }

  @override
  Future<TransactionsData> fetchTransactions({int limit = 20}) async {
    return TransactionsData(
      items: <TransactionRecord>[
        TransactionRecord(
          id: 'txn-1',
          title: '工资入账',
          subtitle: '公司薪酬',
          amount: 12000,
          isIncome: true,
          category: 'income',
          city: '上海',
          createdAt: '2026-03-14T09:00:00',
          status: 'posted',
        ),
      ],
      spendingSummary: const <SpendingSummaryItem>[
        SpendingSummaryItem(category: 'food', totalAmount: 86),
      ],
    );
  }

  @override
  Future<TransferPrecheckResult> precheckTransfer({
    required String payeeName,
    required double amount,
    required ClientContextData context,
  }) async {
    return const TransferPrecheckResult(
      decision: 'review',
      riskLevel: 'high',
      reasons: <String>['当前操作地点异常', '金额较大'],
      confirmationToken: 'confirm-demo',
      assistantMessage: '本次转账需要二次确认。',
    );
  }
}
