import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_base/banking_api.dart';
import 'package:flutter_base/main.dart';

void main() {
  testWidgets('renders dashboard demo content', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    expect(find.text('银行 AI 智能体风控演示'), findsOneWidget);
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

  testWidgets('opens bill sheet', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('账单'));
    await tester.pumpAndSettle();

    expect(find.text('账单明细'), findsOneWidget);
    expect(find.text('工资入账'), findsOneWidget);
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
  Future<TransferConfirmResult> confirmTransfer(
    String confirmationToken,
  ) async {
    return TransferConfirmResult(
      success: true,
      assistantMessage: '转账已完成',
      cashBalance: 2000,
      wealthBalance: 18000,
      totalAssets: 20000,
      latestTransaction: TransactionRecord(
        id: 'txn-demo',
        title: '转账给 小b',
        subtitle: '经智能体风控确认后执行',
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
      userName: '小a',
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
      demoTip: '演示模式已开启：异地、大额、首次收款人会触发智能体风控确认。',
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
      decision: 'interrogate',
      riskLevel: 'high',
      reasons: <String>['当前操作地点异常', '金额较大'],
      confirmationToken: 'confirm-demo',
      assistantMessage: '本次转账需要二次确认。',
      riskClassification: RiskClassificationData(
        riskCategory: '异地大额异常转账',
        riskLevel: 'medium',
        blockHint: false,
        matchedKeywords: <String>['异地', '大额'],
        matchedScenarios: <String>['异地大额异常转账'],
        analysis: '命中异地大额风险场景。',
        followUpQuestions: <String>['请说明你与收款人的关系。', '请说明本次转账用途。'],
        suggestedReplyExamples: <String>['收款人是小b，这次转账用于归还借款。'],
      ),
    );
  }

  @override
  Future<TransferSecondaryCheckResult> secondaryCheckTransfer({
    required String confirmationToken,
    required String userReply,
    required ClientContextData context,
  }) async {
    return const TransferSecondaryCheckResult(
      secondaryDecision: 'pass_secondary',
      reasons: <String>['用户说明合理'],
      finalRiskAfterSecondary: 0.36,
      assistantMessage: '二次校验通过，可继续确认转账。',
      riskClassification: RiskClassificationData(
        riskCategory: '正常转账',
        riskLevel: 'low',
        blockHint: false,
        matchedKeywords: <String>[],
        matchedScenarios: <String>['正常转账'],
        analysis: '当前未命中高风险场景。',
        followUpQuestions: <String>['请说明你与收款人的关系。'],
        suggestedReplyExamples: <String>['收款人是小b，这次转账用于还款。'],
      ),
    );
  }
}
