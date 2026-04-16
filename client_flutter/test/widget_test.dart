import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_base/banking_api.dart';
import 'package:flutter_base/main.dart';

void main() {
  testWidgets('renders dashboard shell', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byIcon(Icons.shield_rounded), findsOneWidget);
    expect(find.byIcon(Icons.receipt_long_rounded), findsOneWidget);
    expect(find.byIcon(Icons.smart_toy_outlined), findsOneWidget);
  });

  testWidgets('opens ai assistant sheet', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.smart_toy_outlined));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('opens bill sheet', (WidgetTester tester) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.receipt_long_rounded));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.close_rounded), findsOneWidget);
    expect(find.text('Salary Credit'), findsOneWidget);
  });

  testWidgets('shows all explain nodes in secondary dialog', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.textContaining('XAI'), findsOneWidget);
    expect(find.textContaining('External Intel'), findsOneWidget);
    expect(find.textContaining('Decision'), findsOneWidget);
  });

  testWidgets('shows cancel transfer action in secondary dialog', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient();
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('取消交易'), findsOneWidget);

    await tester.tap(find.text('取消交易'));
    await tester.pumpAndSettle();

    expect(apiClient.cancelCalled, isTrue);
    expect(apiClient.confirmCallCount, 0);
  });

  testWidgets('allows viewing risk report after secondary check', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient();
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, '这是朋友之间的正常还款。');
    await tester.tap(find.text('提交校验'));
    await tester.pumpAndSettle();

    expect(find.text('查看风险报告'), findsOneWidget);
    await tester.tap(find.text('查看风险报告'));
    await tester.pumpAndSettle();

    expect(find.text('风险报告'), findsOneWidget);
    expect(find.textContaining('风险因子'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('治理上下文'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pump();
    expect(find.text('治理上下文'), findsOneWidget);
    expect(find.text('策略版本'), findsOneWidget);
  });

  testWidgets('shows report center in profile tab and opens report detail', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();

    expect(find.text('风险报告中心'), findsOneWidget);
    expect(find.text('高风险报告'), findsOneWidget);
    expect(find.textContaining('高风险转账报告'), findsOneWidget);

    await tester.tap(find.textContaining('高风险转账报告'));
    await tester.pumpAndSettle();

    expect(find.text('风险报告'), findsOneWidget);
  });

  testWidgets('shows empty state when no high risk reports exist', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MyApp(
        apiClient: _FakeApiClient(
          highRiskReports: const <RiskReportListItemData>[],
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();

    expect(find.text('当前没有高风险报告'), findsOneWidget);
  });

  testWidgets('shows report center retry when list loading fails', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      highRiskReportsError: const ApiException('报告中心暂时不可用'),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();

    expect(find.text('报告中心暂时不可用'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
  });

  testWidgets('shows manual review list in profile tab', (
    WidgetTester tester,
  ) async {
    final ManualReviewSummaryData summary = _sampleManualReviewSummary();
    await tester.pumpWidget(
      MyApp(
        apiClient: _FakeApiClient(
          manualReviews: <ManualReviewSummaryData>[summary],
          manualReviewDetails: <String, ManualReviewDetailData>{
            summary.reviewId: _sampleManualReviewDetail(),
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('我的复核单'), 300);
    await tester.pump();
    expect(find.text('我的复核单'), findsOneWidget);
    expect(find.text(summary.requestReason), findsOneWidget);
  });

  testWidgets('can request manual review from risk report sheet', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient();
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('高风险转账报告'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('申请人工复核'),
      250,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pump();
    expect(find.text('申请人工复核'), findsOneWidget);
    await tester.tap(find.text('申请人工复核'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byType(TextField).last,
      '对方身份和资金用途仍然存在明显矛盾，需要人工进一步核验。',
    );
    await tester.tap(find.text('提交复核申请'));
    await tester.pumpAndSettle();

    expect(apiClient.createManualReviewCallCount, 1);
    expect(find.text('复核单详情'), findsOneWidget);
    expect(find.textContaining('申请原因'), findsOneWidget);
  });

  testWidgets('review console can start and close review case', (
    WidgetTester tester,
  ) async {
    final ManualReviewSummaryData summary = _sampleManualReviewSummary();
    final ManualReviewDetailData detail = _sampleManualReviewDetail();
    final _FakeApiClient apiClient = _FakeApiClient(
      manualReviews: <ManualReviewSummaryData>[summary],
      manualReviewQueue: <ManualReviewQueueItemData>[
        _sampleManualReviewQueueItem(),
      ],
      manualReviewDetails: <String, ManualReviewDetailData>{
        summary.reviewId: detail,
      },
    );

    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('复核处理台'));
    await tester.pumpAndSettle();

    expect(find.text('待处理'), findsWidgets);
    await tester.tap(find.text(detail.headline).first);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('开始处理'), 250);
    await tester.pump();
    await tester.tap(find.text('开始处理'));
    await tester.pumpAndSettle();
    expect(apiClient.updateManualReviewCallCount, 1);

    await tester.scrollUntilVisible(find.text('关闭复核单'), 250);
    await tester.pump();
    await tester.tap(find.text('关闭复核单'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, '维持原结论，建议继续通过官方渠道核验。');
    await tester.tap(find.text('提交处理结果'));
    await tester.pumpAndSettle();

    expect(apiClient.updateManualReviewCallCount, 2);
    await tester.scrollUntilVisible(find.text('当前复核单已关闭，无进一步处理动作。'), 250);
    await tester.pump();
    expect(find.text('当前复核单已关闭，无进一步处理动作。'), findsOneWidget);
  });

  testWidgets('manual review filter chips can show closed reviews only', (
    WidgetTester tester,
  ) async {
    final ManualReviewSummaryData submitted = _sampleManualReviewSummary();
    final ManualReviewSummaryData closed = _sampleClosedManualReviewSummary();
    await tester.pumpWidget(
      MyApp(
        apiClient: _FakeApiClient(
          manualReviews: <ManualReviewSummaryData>[submitted, closed],
          manualReviewDetails: <String, ManualReviewDetailData>{
            submitted.reviewId: _sampleManualReviewDetail(),
            closed.reviewId: _sampleClosedManualReviewDetail(),
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('我的'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('我的复核单'), 300);
    await tester.pump();

    await tester.tap(find.widgetWithText(ChoiceChip, '已关闭').first);
    await tester.pumpAndSettle();

    expect(find.text(closed.requestReason), findsOneWidget);
    expect(find.text(submitted.requestReason), findsNothing);
  });

  testWidgets(
    'closed manual review timeline keeps distinct in-review timestamp',
    (WidgetTester tester) async {
      final ManualReviewSummaryData closed = _sampleClosedManualReviewSummary();
      await tester.pumpWidget(
        MyApp(
          apiClient: _FakeApiClient(
            manualReviews: <ManualReviewSummaryData>[closed],
            manualReviewDetails: <String, ManualReviewDetailData>{
              closed.reviewId: _sampleClosedManualReviewDetail(),
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(find.text('我的复核单'), 300);
      await tester.pump();
      await tester.tap(find.text(closed.requestReason));
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('复核时间线'),
        250,
        scrollable: find.byType(Scrollable).last,
      );
      await tester.pump();
      expect(find.text('2026-04-10T09:00:00Z'), findsWidgets);
      expect(find.text('2026-04-10T09:30:00Z'), findsOneWidget);
      expect(find.text('2026-04-10T11:00:00Z'), findsWidgets);
    },
  );

  testWidgets('shows unified invalid input message for empty ai input', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MyApp(apiClient: _FakeApiClient()));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.smart_toy_outlined));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.send_rounded));
    await tester.pump();

    expect(find.text('无效输入，请按照要求输入'), findsOneWidget);
  });

  testWidgets('single-round interrogate does not continue to confirm', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      secondaryResponse: const TransferSecondaryCheckResult(
        secondaryDecision: 'interrogate',
        reasons: <String>['need more evidence'],
        finalRiskAfterSecondary: 0.66,
        assistantMessage: 'Secondary explanation is insufficient.',
        riskClassification: RiskClassificationData(
          riskCategory: 'borrow_money_impersonation',
          riskLevel: 'medium',
          blockHint: false,
          matchedKeywords: <String>['borrow money'],
          matchedScenarios: <String>['borrow_money_impersonation'],
          analysis: 'Need a more direct explanation.',
          followUpQuestions: <String>[
            'What is your relationship with the payee?',
          ],
          suggestedReplyExamples: <String>['The payee is my colleague.'],
        ),
        explainPack: ExplainPackData(
          headline: 'Secondary explanation insufficient',
          recommendedAction: 'Stop and verify before trying again.',
          scoreBreakdown: RiskScoreBreakdownData(
            flagS: 0.62,
            gBehavior: 0.41,
            gDynamic: 0.74,
            finalRisk: 0.66,
          ),
          nodes: <ExplainNodeData>[
            ExplainNodeData(
              id: 'decision',
              title: 'Decision',
              level: 'medium',
              summary: 'Still needs review',
              detail: 'Do not continue with confirmation.',
              score: 0.66,
            ),
          ],
        ),
      ),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, '我就是想转账。');
    await tester.tap(find.text('提交校验'));
    await tester.pumpAndSettle();

    expect(find.text('二次说明未通过'), findsOneWidget);
    expect(apiClient.confirmCallCount, 0);
  });

  testWidgets('shows busy hint for delayed secondary-check', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      secondaryDelay: const Duration(milliseconds: 2200),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, '这是朋友之间的正常还款。');
    await tester.tap(find.text('提交校验'));
    await tester.pump(const Duration(milliseconds: 1200));

    expect(find.textContaining('二次校验 处理中'), findsOneWidget);
    expect(apiClient.secondaryCallCount, 1);
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 300));
  });

  testWidgets('shows long-wait hint after 10s for delayed secondary-check', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      secondaryDelay: const Duration(seconds: 11),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, '关系明确，用途明确，不涉及验证码。');
    await tester.tap(find.text('提交校验'));
    await tester.pump(const Duration(milliseconds: 10300));

    expect(find.textContaining('仍在等待模型/服务响应'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 300));
  });

  testWidgets('shows busy hint for delayed confirm', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      precheckResponse: const TransferPrecheckResult(
        decision: 'pass',
        riskLevel: 'low',
        flagS: 0.1,
        gBehavior: 0.1,
        gDynamic: 0.1,
        finalRisk: 0.1,
        reasons: <String>['normal transfer'],
        confirmationToken: 'confirm-demo',
        assistantMessage: '可继续转账。',
        riskClassification: RiskClassificationData(
          riskCategory: 'normal_transfer',
          riskLevel: 'low',
          blockHint: false,
          matchedKeywords: <String>['normal'],
          matchedScenarios: <String>['normal_transfer'],
          analysis: 'normal transfer',
          followUpQuestions: <String>[],
          suggestedReplyExamples: <String>[],
        ),
      ),
      confirmDelay: const Duration(milliseconds: 2200),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pump(const Duration(milliseconds: 1200));

    expect(find.textContaining('确认转账 处理中'), findsOneWidget);
    expect(apiClient.confirmCallCount, 1);
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 300));
  });

  testWidgets('shows busy hint for delayed cancel', (
    WidgetTester tester,
  ) async {
    final _FakeApiClient apiClient = _FakeApiClient(
      cancelDelay: const Duration(milliseconds: 2200),
    );
    await tester.pumpWidget(MyApp(apiClient: apiClient));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.shield_rounded));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('取消交易'));
    await tester.pump(const Duration(milliseconds: 1200));

    expect(find.textContaining('取消交易 处理中'), findsOneWidget);
    expect(apiClient.cancelCallCount, 1);
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 300));
  });

  mainDataContractTests();
}

void mainDataContractTests() {
  test('builds fallback explain pack for precheck payload', () {
    final TransferPrecheckResult result = TransferPrecheckResult.fromJson(
      <String, dynamic>{
        'decision': 'interrogate',
        'risk_level': 'medium',
        'flag_s': 0.61,
        'g_behavior': 0.44,
        'g_dynamic': 0.72,
        'final_risk': 0.59,
        'reasons': <String>['remote city', 'new payee'],
        'confirmation_token': 'demo-token',
        'assistant_message': 'Please confirm the transfer.',
        'risk_classification': <String, dynamic>{
          'risk_category': 'remote_large_transfer',
          'risk_level': 'medium',
          'block_hint': false,
          'matched_keywords': <String>['remote', 'large_amount'],
          'matched_scenarios': <String>['remote_large_transfer'],
          'analysis': 'Matched remote large transfer risk scenario.',
          'follow_up_questions': <String>['What is the relationship?'],
          'suggested_reply_examples': <String>['This is a normal repayment.'],
        },
      },
    );

    expect(result.explainPack.headline, isNotEmpty);
    expect(result.explainPack.scoreBreakdown.finalRisk, closeTo(0.59, 0.0001));
    expect(result.explainPack.nodes, isNotEmpty);
    expect(result.explainPack.nodes.first.score, closeTo(0.72, 0.0001));
  });

  test('parses explain pack for secondary payload', () {
    final TransferSecondaryCheckResult result =
        TransferSecondaryCheckResult.fromJson(<String, dynamic>{
          'secondary_decision': 'block_secondary',
          'reasons': <String>['high risk keyword'],
          'final_risk_after_secondary': 0.93,
          'assistant_message': 'Secondary check failed.',
          'risk_classification': <String, dynamic>{
            'risk_category': 'safe_account_scam',
            'risk_level': 'high',
            'block_hint': true,
            'matched_keywords': <String>['safe account'],
            'matched_scenarios': <String>['safe_account_scam'],
            'analysis': 'Matched high-risk scam phrase.',
            'follow_up_questions': <String>['Did anyone ask for a code?'],
            'suggested_reply_examples': <String>[
              'The caller asked for a verification code.',
            ],
          },
          'explain_pack': <String, dynamic>{
            'headline': 'Secondary check failed',
            'recommended_action': 'Stop the transfer and contact support',
            'score_breakdown': <String, dynamic>{
              'flag_s': 0.8,
              'g_behavior': 0.7,
              'g_dynamic': 0.95,
              'final_risk': 0.93,
            },
            'nodes': <Map<String, dynamic>>[
              <String, dynamic>{
                'id': 'semantic',
                'title': 'Semantic Signal',
                'level': 'high',
                'summary': 'Matched scam language',
                'detail': 'Contains safe-account and code-sharing cues',
                'score': 0.95,
              },
            ],
          },
        });

    expect(result.explainPack.headline, 'Secondary check failed');
    expect(result.explainPack.nodes.first.title, 'Semantic Signal');
    expect(result.explainPack.scoreBreakdown.finalRisk, closeTo(0.93, 0.0001));
    expect(result.explainPack.nodes.first.score, closeTo(0.95, 0.0001));
  });

  test('builds fallback explain pack for single-round interrogate payload', () {
    final TransferSecondaryCheckResult result =
        TransferSecondaryCheckResult.fromJson(<String, dynamic>{
          'secondary_decision': 'interrogate',
          'reasons': <String>['need more evidence'],
          'final_risk_after_secondary': 0.66,
          'assistant_message': 'Secondary explanation is insufficient.',
          'risk_classification': <String, dynamic>{
            'risk_category': 'borrow_money_impersonation',
            'risk_level': 'medium',
            'block_hint': false,
            'matched_keywords': <String>['borrow money'],
            'matched_scenarios': <String>['borrow_money_impersonation'],
            'analysis': 'Need a more direct explanation.',
            'follow_up_questions': <String>[
              'What is your relationship with the payee?',
            ],
            'suggested_reply_examples': <String>['The payee is my colleague.'],
          },
        });

    expect(result.explainPack.headline, '二次说明未通过');
    expect(result.explainPack.recommendedAction, '当前转账不得继续确认，请关闭或取消交易。');
    expect(result.explainPack.scoreBreakdown.finalRisk, closeTo(0.66, 0.0001));
  });
}

ManualReviewSummaryData _sampleManualReviewSummary() {
  return const ManualReviewSummaryData(
    reviewId: 'review-001',
    confirmationToken: 'report-high-001',
    status: 'submitted',
    outcome: null,
    requestReason: '这笔交易的用途说明和关系描述有冲突，需要人工进一步核验。',
    headline: '高风险转账报告',
    overallRiskLevel: 'high',
    submittedAt: '2026-04-10T10:00:00Z',
    updatedAt: '2026-04-10T10:00:00Z',
    closedAt: null,
  );
}

ManualReviewQueueItemData _sampleManualReviewQueueItem() {
  return const ManualReviewQueueItemData(
    reviewId: 'review-001',
    confirmationToken: 'report-high-001',
    userId: '小a',
    status: 'submitted',
    outcome: null,
    requestReason: '这笔交易的用途说明和关系描述有冲突，需要人工进一步核验。',
    headline: '高风险转账报告',
    overallRiskLevel: 'high',
    submittedAt: '2026-04-10T10:00:00Z',
    updatedAt: '2026-04-10T10:00:00Z',
    closedAt: null,
  );
}

ManualReviewDetailData _sampleManualReviewDetail() {
  return const ManualReviewDetailData(
    reviewId: 'review-001',
    confirmationToken: 'report-high-001',
    status: 'submitted',
    outcome: null,
    requestReason: '这笔交易的用途说明和关系描述有冲突，需要人工进一步核验。',
    headline: '高风险转账报告',
    overallRiskLevel: 'high',
    submittedAt: '2026-04-10T10:00:00Z',
    updatedAt: '2026-04-10T10:00:00Z',
    closedAt: null,
    inReviewAt: null,
    reviewNote: null,
    reviewerId: null,
    requestSnapshot: ManualReviewSnapshotData(
      headline: '高风险转账报告',
      overallRiskLevel: 'high',
      riskSummary: '该交易涉及高风险语义和外部情报命中。',
      riskCategory: 'safe_account_scam',
      policyVersion: 'secondary_policy_v1',
      generationMode: 'fallback',
      generatedAt: '2026-04-09T12:00:00Z',
      evidence: <String>['外部情报命中高风险名单', '用户解释与场景分类冲突'],
      governance: RiskReportGovernanceData(
        reportVersion: 'v2',
        policyVersion: 'secondary_policy_v1',
        generationMode: 'fallback',
        sourceStage: 'secondary-check',
        secondaryDecision: 'block_secondary',
        riskCategory: 'safe_account_scam',
        externalIntelligenceLevel: 'medium',
        traceEvents: <String>['secondary_decided', 'risk_report_generated'],
      ),
    ),
  );
}

ManualReviewSummaryData _sampleClosedManualReviewSummary() {
  return const ManualReviewSummaryData(
    reviewId: 'review-002',
    confirmationToken: 'report-high-002',
    status: 'closed',
    outcome: 'upheld',
    requestReason: '该复核单已经关闭，用于测试状态筛选。',
    headline: '已关闭高风险转账报告',
    overallRiskLevel: 'high',
    submittedAt: '2026-04-10T09:00:00Z',
    updatedAt: '2026-04-10T11:00:00Z',
    closedAt: '2026-04-10T11:00:00Z',
  );
}

ManualReviewDetailData _sampleClosedManualReviewDetail() {
  return const ManualReviewDetailData(
    reviewId: 'review-002',
    confirmationToken: 'report-high-002',
    status: 'closed',
    outcome: 'upheld',
    requestReason: '该复核单已经关闭，用于测试状态筛选。',
    headline: '已关闭高风险转账报告',
    overallRiskLevel: 'high',
    submittedAt: '2026-04-10T09:00:00Z',
    updatedAt: '2026-04-10T11:00:00Z',
    closedAt: '2026-04-10T11:00:00Z',
    inReviewAt: '2026-04-10T09:30:00Z',
    reviewNote: '维持原结论。',
    reviewerId: 'demo-reviewer',
    requestSnapshot: ManualReviewSnapshotData(
      headline: '已关闭高风险转账报告',
      overallRiskLevel: 'high',
      riskSummary: '关闭状态的复核样例。',
      riskCategory: 'safe_account_scam',
      policyVersion: 'secondary_policy_v1',
      generationMode: 'fallback',
      generatedAt: '2026-04-09T11:00:00Z',
      evidence: <String>['证据 A', '证据 B'],
      governance: RiskReportGovernanceData(
        reportVersion: 'v2',
        policyVersion: 'secondary_policy_v1',
        generationMode: 'fallback',
        sourceStage: 'secondary-check',
        secondaryDecision: 'block_secondary',
        riskCategory: 'safe_account_scam',
        externalIntelligenceLevel: 'medium',
        traceEvents: <String>['secondary_decided', 'risk_report_generated'],
      ),
    ),
  );
}

class _FakeApiClient implements BankingApiClient {
  _FakeApiClient({
    this.precheckResponse,
    List<RiskReportListItemData>? highRiskReports,
    List<ManualReviewSummaryData>? manualReviews,
    List<ManualReviewQueueItemData>? manualReviewQueue,
    Map<String, ManualReviewDetailData>? manualReviewDetails,
    this.highRiskReportsError,
    this.secondaryResponse = const TransferSecondaryCheckResult(
      secondaryDecision: 'pass_secondary',
      reasons: <String>['user explanation looks reasonable'],
      finalRiskAfterSecondary: 0.36,
      assistantMessage: 'Secondary check passed. You may continue.',
      riskClassification: RiskClassificationData(
        riskCategory: 'normal_transfer',
        riskLevel: 'low',
        blockHint: false,
        matchedKeywords: <String>[],
        matchedScenarios: <String>['normal_transfer'],
        analysis: 'No high-risk scenario was matched after the explanation.',
        followUpQuestions: <String>[
          'What is your relationship with the payee?',
        ],
        suggestedReplyExamples: <String>[
          'This is a normal repayment to a known friend.',
        ],
      ),
      explainPack: ExplainPackData(
        headline: 'Secondary check passed',
        recommendedAction: 'Continue with transfer confirmation.',
        scoreBreakdown: RiskScoreBreakdownData(
          flagS: 0.0,
          gBehavior: 0.0,
          gDynamic: 0.0,
          finalRisk: 0.36,
        ),
        nodes: <ExplainNodeData>[
          ExplainNodeData(
            id: 'secondary',
            title: 'Secondary Decision Basis',
            level: 'low',
            summary: 'The explanation is consistent.',
            detail:
                'The relationship and purpose are coherent and do not include high-risk instructions.',
            score: 0.36,
          ),
        ],
      ),
    ),
    this.secondaryDelay = Duration.zero,
    this.confirmDelay = Duration.zero,
    this.cancelDelay = Duration.zero,
  }) : _highRiskReports = List<RiskReportListItemData>.from(
         highRiskReports ??
             const <RiskReportListItemData>[
               RiskReportListItemData(
                 confirmationToken: 'report-high-001',
                 headline: '高风险转账报告',
                 overallRiskLevel: 'high',
                 riskSummary: '该交易涉及高风险语义和外部情报命中。',
                 riskCategory: 'safe_account_scam',
                 policyVersion: 'secondary_policy_v1',
                 generationMode: 'fallback',
                 generatedAt: '2026-04-10T09:30:00Z',
               ),
             ],
       ),
       _manualReviews = List<ManualReviewSummaryData>.from(
         manualReviews ?? const <ManualReviewSummaryData>[],
       ),
       _manualReviewQueue = List<ManualReviewQueueItemData>.from(
         manualReviewQueue ?? const <ManualReviewQueueItemData>[],
       ),
       _manualReviewDetails = Map<String, ManualReviewDetailData>.from(
         manualReviewDetails ?? <String, ManualReviewDetailData>{},
       );

  final TransferPrecheckResult? precheckResponse;
  final List<RiskReportListItemData> _highRiskReports;
  final List<ManualReviewSummaryData> _manualReviews;
  final List<ManualReviewQueueItemData> _manualReviewQueue;
  final Map<String, ManualReviewDetailData> _manualReviewDetails;
  final ApiException? highRiskReportsError;
  final TransferSecondaryCheckResult secondaryResponse;
  final Duration secondaryDelay;
  final Duration confirmDelay;
  final Duration cancelDelay;
  bool cancelCalled = false;
  int confirmCallCount = 0;
  int secondaryCallCount = 0;
  int cancelCallCount = 0;
  int createManualReviewCallCount = 0;
  int updateManualReviewCallCount = 0;

  @override
  Future<ChatReply> chat({
    required List<ChatTurn> messages,
    required ClientContextData context,
  }) async {
    return const ChatReply(
      assistantMessage: 'Current available cash balance is 2500.00 CNY.',
      usedTools: <ToolUsageItem>[
        ToolUsageItem(name: 'get_account_summary', summary: 'Account snapshot'),
      ],
      suggestedActions: <SuggestedActionItem>[
        SuggestedActionItem(label: 'Start transfer', action: 'open_transfer'),
      ],
    );
  }

  @override
  Future<RiskReportListData> fetchHighRiskReports() async {
    if (highRiskReportsError != null) {
      throw highRiskReportsError!;
    }
    return RiskReportListData(items: _highRiskReports);
  }

  @override
  Future<TransferConfirmResult> confirmTransfer(
    String confirmationToken,
  ) async {
    confirmCallCount += 1;
    if (confirmDelay > Duration.zero) {
      await Future<void>.delayed(confirmDelay);
    }
    return TransferConfirmResult(
      success: true,
      assistantMessage: 'Transfer completed.',
      cashBalance: 2000,
      wealthBalance: 18000,
      totalAssets: 20000,
      latestTransaction: TransactionRecord(
        id: 'txn-demo',
        title: 'Transfer to Xiao B',
        subtitle: 'Executed after risk confirmation',
        amount: 500,
        isIncome: false,
        category: 'transfer',
        city: 'Shanghai',
        createdAt: '2026-03-16T10:00:00',
        status: 'posted',
      ),
    );
  }

  @override
  Future<TransferCancelResult> cancelTransfer(String confirmationToken) async {
    cancelCalled = true;
    cancelCallCount += 1;
    if (cancelDelay > Duration.zero) {
      await Future<void>.delayed(cancelDelay);
    }
    return TransferCancelResult(
      success: true,
      status: 'cancelled',
      confirmationToken: confirmationToken,
      assistantMessage: 'Transfer cancelled.',
    );
  }

  @override
  Future<DashboardData> fetchDashboard() async {
    return DashboardData(
      userName: 'Demo User',
      cashBalance: 2500,
      wealthBalance: 18000,
      totalAssets: 20500,
      currency: 'CNY',
      recentTransactions: <TransactionRecord>[
        TransactionRecord(
          id: 'txn-1',
          title: 'Salary Credit',
          subtitle: 'Monthly payroll',
          amount: 12000,
          isIncome: true,
          category: 'income',
          city: 'Shanghai',
          createdAt: '2026-03-14T09:00:00',
          status: 'posted',
        ),
      ],
      spendingSummary: const <SpendingSummaryItem>[
        SpendingSummaryItem(category: 'food', totalAmount: 86),
      ],
      demoTip:
          'Demo mode is enabled: remote, large and first-time payee patterns trigger checks.',
    );
  }

  @override
  Future<TransactionsData> fetchTransactions({int limit = 20}) async {
    return TransactionsData(
      items: <TransactionRecord>[
        TransactionRecord(
          id: 'txn-1',
          title: 'Salary Credit',
          subtitle: 'Monthly payroll',
          amount: 12000,
          isIncome: true,
          category: 'income',
          city: 'Shanghai',
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
    if (precheckResponse != null) {
      return precheckResponse!;
    }
    return const TransferPrecheckResult(
      decision: 'interrogate',
      riskLevel: 'high',
      flagS: 0.62,
      gBehavior: 0.41,
      gDynamic: 0.74,
      finalRisk: 0.58,
      reasons: <String>['location anomaly', 'large amount'],
      confirmationToken: 'confirm-demo',
      assistantMessage: 'Need secondary confirmation.',
      riskClassification: RiskClassificationData(
        riskCategory: 'remote_large_transfer',
        riskLevel: 'medium',
        blockHint: false,
        matchedKeywords: <String>['remote', 'large_amount'],
        matchedScenarios: <String>['remote_large_transfer'],
        analysis: 'Matched remote large transfer risk scenario.',
        followUpQuestions: <String>[
          'What is your relationship with the payee?',
          'What is the purpose of this transfer?',
        ],
        suggestedReplyExamples: <String>[
          'The payee is Xiao B, this transfer is for a normal repayment.',
        ],
      ),
      explainPack: ExplainPackData(
        headline: 'Secondary confirmation required',
        recommendedAction:
            'Explain the relationship and transfer purpose before continuing.',
        scoreBreakdown: RiskScoreBreakdownData(
          flagS: 0.62,
          gBehavior: 0.41,
          gDynamic: 0.74,
          finalRisk: 0.58,
        ),
        nodes: <ExplainNodeData>[
          ExplainNodeData(
            id: 'static',
            title: 'Static Risk',
            level: 'medium',
            summary: 'Remote city and new payee.',
            detail:
                'The current city is unusual and the payee has not been seen recently.',
            score: 0.62,
          ),
          ExplainNodeData(
            id: 'behavior',
            title: 'Behavior Signal',
            level: 'medium',
            summary: 'Typing pause and page switching were detected.',
            detail:
                'The precheck observed longer input duration and multiple interaction signals.',
            score: 0.41,
          ),
          ExplainNodeData(
            id: 'semantic',
            title: 'Semantic Risk',
            level: 'medium',
            summary: 'Matched remote large transfer scenario.',
            detail:
                'The transfer context contains remote-city and large-amount cues.',
            score: 0.74,
          ),
          ExplainNodeData(
            id: 'external_intelligence',
            title: 'External Intel',
            level: 'medium',
            summary: 'External negative intelligence flagged the payee.',
            detail:
                'Recent complaints suggest abnormal collection behavior and require more checks.',
            score: 0.55,
          ),
          ExplainNodeData(
            id: 'decision',
            title: 'Decision',
            level: 'medium',
            summary: 'Escalate to secondary interrogation.',
            detail:
                'Continue only after the user provides a credible explanation.',
            score: 0.58,
          ),
        ],
      ),
    );
  }

  @override
  Future<TransferSecondaryCheckResult> secondaryCheckTransfer({
    required String confirmationToken,
    required String userReply,
    required ClientContextData context,
  }) async {
    secondaryCallCount += 1;
    if (secondaryDelay > Duration.zero) {
      await Future<void>.delayed(secondaryDelay);
    }
    return secondaryResponse;
  }

  @override
  Future<RiskReportData> fetchRiskReport(String confirmationToken) async {
    return RiskReportData(
      confirmationToken: confirmationToken,
      headline: confirmationToken == 'report-high-001'
          ? '高风险转账报告'
          : '风险报告 · ${confirmationToken.substring(0, 6)}',
      overallRiskLevel: confirmationToken == 'report-high-001'
          ? 'high'
          : 'medium',
      riskSummary: confirmationToken == 'report-high-001'
          ? '该交易涉及高风险语义、外部情报命中和异常用途说明。'
          : '结合用户画像、文本与分类，当前转账属于中风险示例。',
      riskFactors: confirmationToken == 'report-high-001'
          ? <String>['语义提示：安全账户', '外部情报：名单命中', '二次说明未通过']
          : <String>['语义提示：安全账户', '外部情报：名单命中'],
      recommendedAction: '建议人工核实收款人身份后再决定是否继续。重点复核：核实收款人关系与资金用途。',
      evidence: confirmationToken == 'report-high-001'
          ? <String>['外部情报命中高风险名单', '用户解释与场景分类冲突']
          : <String>['用户解释中提及验证码/安全账户', '分类得分高于阈值'],
      governance: const RiskReportGovernanceData(
        reportVersion: 'v2',
        policyVersion: 'secondary_policy_v1',
        generationMode: 'fallback',
        sourceStage: 'secondary-check',
        secondaryDecision: 'pass_secondary',
        riskCategory: 'normal_transfer',
        externalIntelligenceLevel: 'medium',
        traceEvents: <String>['secondary_decided', 'risk_report_generated'],
      ),
      generatedAt: '2026-04-09T12:00:00Z',
    );
  }

  @override
  Future<ManualReviewListData> fetchManualReviews({
    String status = 'all',
  }) async {
    final List<ManualReviewSummaryData> items = status == 'all'
        ? _manualReviews
        : _manualReviews
              .where((ManualReviewSummaryData item) => item.status == status)
              .toList();
    return ManualReviewListData(
      items: List<ManualReviewSummaryData>.from(items),
    );
  }

  @override
  Future<ManualReviewSummaryData> createManualReview({
    required String confirmationToken,
    required ManualReviewCreateRequestData request,
  }) async {
    createManualReviewCallCount += 1;
    final String reviewId =
        'review-${createManualReviewCallCount.toString().padLeft(3, '0')}';
    final RiskReportData report = await fetchRiskReport(confirmationToken);
    final ManualReviewSummaryData summary = ManualReviewSummaryData(
      reviewId: reviewId,
      confirmationToken: confirmationToken,
      status: 'submitted',
      outcome: null,
      requestReason: request.requestReason,
      headline: report.headline,
      overallRiskLevel: report.overallRiskLevel,
      submittedAt: '2026-04-10T10:00:00Z',
      updatedAt: '2026-04-10T10:00:00Z',
      closedAt: null,
    );
    _manualReviews.insert(0, summary);
    _manualReviewQueue.insert(
      0,
      ManualReviewQueueItemData(
        reviewId: reviewId,
        confirmationToken: confirmationToken,
        userId: '小a',
        status: 'submitted',
        outcome: null,
        requestReason: request.requestReason,
        headline: report.headline,
        overallRiskLevel: report.overallRiskLevel,
        submittedAt: summary.submittedAt,
        updatedAt: summary.updatedAt,
        closedAt: null,
      ),
    );
    _manualReviewDetails[reviewId] = ManualReviewDetailData(
      reviewId: reviewId,
      confirmationToken: confirmationToken,
      status: 'submitted',
      outcome: null,
      requestReason: request.requestReason,
      headline: report.headline,
      overallRiskLevel: report.overallRiskLevel,
      submittedAt: summary.submittedAt,
      updatedAt: summary.updatedAt,
      closedAt: null,
      inReviewAt: null,
      reviewNote: null,
      reviewerId: null,
      requestSnapshot: ManualReviewSnapshotData(
        headline: report.headline,
        overallRiskLevel: report.overallRiskLevel,
        riskSummary: report.riskSummary,
        riskCategory: report.governance.riskCategory,
        policyVersion: report.governance.policyVersion,
        generationMode: report.governance.generationMode,
        generatedAt: report.generatedAt,
        evidence: report.evidence,
        governance: report.governance,
      ),
    );
    return summary;
  }

  @override
  Future<ManualReviewDetailData> fetchManualReviewDetail(
    String reviewId,
  ) async {
    return _manualReviewDetails[reviewId] ??
        (throw const ApiException('未找到对应复核单'));
  }

  @override
  Future<ManualReviewQueueData> fetchManualReviewQueue() async {
    return ManualReviewQueueData(
      items: List<ManualReviewQueueItemData>.from(_manualReviewQueue),
    );
  }

  @override
  Future<ManualReviewDetailData> updateManualReview({
    required String reviewId,
    required ManualReviewUpdateRequestData request,
  }) async {
    updateManualReviewCallCount += 1;
    final ManualReviewDetailData current =
        _manualReviewDetails[reviewId] ??
        (throw const ApiException('未找到对应复核单'));
    final ManualReviewDetailData updated = ManualReviewDetailData(
      reviewId: current.reviewId,
      confirmationToken: current.confirmationToken,
      status: request.status,
      outcome: request.outcome ?? current.outcome,
      requestReason: current.requestReason,
      headline: current.headline,
      overallRiskLevel: current.overallRiskLevel,
      submittedAt: current.submittedAt,
      updatedAt: '2026-04-10T11:00:00Z',
      closedAt: request.status == 'closed' ? '2026-04-10T11:00:00Z' : null,
      inReviewAt: request.status == 'in_review'
          ? '2026-04-10T10:30:00Z'
          : current.inReviewAt,
      reviewNote: request.reviewNote ?? current.reviewNote,
      reviewerId: request.reviewerId ?? current.reviewerId,
      requestSnapshot: current.requestSnapshot,
    );
    _manualReviewDetails[reviewId] = updated;
    final int summaryIndex = _manualReviews.indexWhere(
      (ManualReviewSummaryData item) => item.reviewId == reviewId,
    );
    if (summaryIndex >= 0) {
      _manualReviews[summaryIndex] = ManualReviewSummaryData(
        reviewId: updated.reviewId,
        confirmationToken: updated.confirmationToken,
        status: updated.status,
        outcome: updated.outcome,
        requestReason: updated.requestReason,
        headline: updated.headline,
        overallRiskLevel: updated.overallRiskLevel,
        submittedAt: updated.submittedAt,
        updatedAt: updated.updatedAt,
        closedAt: updated.closedAt,
      );
    }
    final int queueIndex = _manualReviewQueue.indexWhere(
      (ManualReviewQueueItemData item) => item.reviewId == reviewId,
    );
    if (request.status == 'closed') {
      if (queueIndex >= 0) {
        _manualReviewQueue.removeAt(queueIndex);
      }
    } else if (queueIndex >= 0) {
      final ManualReviewQueueItemData currentQueue =
          _manualReviewQueue[queueIndex];
      _manualReviewQueue[queueIndex] = ManualReviewQueueItemData(
        reviewId: currentQueue.reviewId,
        confirmationToken: currentQueue.confirmationToken,
        userId: currentQueue.userId,
        status: request.status,
        outcome: updated.outcome,
        requestReason: currentQueue.requestReason,
        headline: currentQueue.headline,
        overallRiskLevel: currentQueue.overallRiskLevel,
        submittedAt: currentQueue.submittedAt,
        updatedAt: updated.updatedAt,
        closedAt: updated.closedAt,
      );
    }
    return updated;
  }
}
