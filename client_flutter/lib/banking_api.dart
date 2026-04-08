import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

String defaultApiBaseUrl() {
  if (kIsWeb) {
    return const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000',
    );
  }
  return const String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}

abstract class BankingApiClient {
  Future<DashboardData> fetchDashboard();
  Future<TransactionsData> fetchTransactions({int limit = 20});
  Future<TransferPrecheckResult> precheckTransfer({
    required String payeeName,
    required double amount,
    required ClientContextData context,
  });
  Future<TransferCancelResult> cancelTransfer(String confirmationToken);
  Future<TransferConfirmResult> confirmTransfer(String confirmationToken);
  Future<TransferSecondaryCheckResult> secondaryCheckTransfer({
    required String confirmationToken,
    required String userReply,
    required ClientContextData context,
  });
  Future<ChatReply> chat({
    required List<ChatTurn> messages,
    required ClientContextData context,
  });
}

class HttpBankingApiClient implements BankingApiClient {
  HttpBankingApiClient({
    http.Client? client,
    String? baseUrl,
  }) : _client = client ?? http.Client(),
       _baseUrl = baseUrl ?? defaultApiBaseUrl();

  final http.Client _client;
  final String _baseUrl;

  @override
  Future<DashboardData> fetchDashboard() async {
    final response = await _client.get(Uri.parse('$_baseUrl/api/v1/dashboard'));
    return DashboardData.fromJson(_decode(response));
  }

  @override
  Future<TransactionsData> fetchTransactions({int limit = 20}) async {
    final response = await _client.get(
      Uri.parse('$_baseUrl/api/v1/transactions?limit=$limit'),
    );
    return TransactionsData.fromJson(_decode(response));
  }

  @override
  Future<TransferPrecheckResult> precheckTransfer({
    required String payeeName,
    required double amount,
    required ClientContextData context,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/api/v1/transfers/precheck'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, dynamic>{
        'payee_name': payeeName,
        'amount': amount,
        'context': context.toJson(),
      }),
    );
    return TransferPrecheckResult.fromJson(_decode(response));
  }

  @override
  Future<TransferConfirmResult> confirmTransfer(String confirmationToken) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/api/v1/transfers/confirm'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, dynamic>{
        'confirmation_token': confirmationToken,
      }),
    );
    return TransferConfirmResult.fromJson(_decode(response));
  }

  @override
  Future<TransferCancelResult> cancelTransfer(String confirmationToken) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/api/v1/transfers/cancel'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, dynamic>{
        'confirmation_token': confirmationToken,
      }),
    );
    return TransferCancelResult.fromJson(_decode(response));
  }

  @override
  Future<TransferSecondaryCheckResult> secondaryCheckTransfer({
    required String confirmationToken,
    required String userReply,
    required ClientContextData context,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/api/v1/transfers/secondary-check'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, dynamic>{
        'confirmation_token': confirmationToken,
        'user_reply': userReply,
        'context': context.toJson(),
      }),
    );
    return TransferSecondaryCheckResult.fromJson(_decode(response));
  }

  @override
  Future<ChatReply> chat({
    required List<ChatTurn> messages,
    required ClientContextData context,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/api/v1/agent/chat'),
      headers: const <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(<String, dynamic>{
        'messages': messages.map((ChatTurn message) => message.toJson()).toList(),
        'context': context.toJson(),
      }),
    );
    return ChatReply.fromJson(_decode(response));
  }

  Map<String, dynamic> _decode(http.Response response) {
    final Map<String, dynamic> body =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }
    throw ApiException(
      body['detail']?.toString() ?? body['message']?.toString() ?? '请求失败',
    );
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class DashboardData {
  const DashboardData({
    required this.userName,
    required this.cashBalance,
    required this.wealthBalance,
    required this.totalAssets,
    required this.currency,
    required this.recentTransactions,
    required this.spendingSummary,
    required this.demoTip,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      userName: json['user_name'] as String? ?? '演示用户',
      cashBalance: (json['cash_balance'] as num?)?.toDouble() ?? 0,
      wealthBalance: (json['wealth_balance'] as num?)?.toDouble() ?? 0,
      totalAssets: (json['total_assets'] as num?)?.toDouble() ?? 0,
      currency: json['currency'] as String? ?? 'CNY',
      recentTransactions: (json['recent_transactions'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) =>
                TransactionRecord.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      spendingSummary: (json['spending_summary'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) =>
                SpendingSummaryItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      demoTip: json['demo_tip'] as String? ?? '',
    );
  }

  final String userName;
  final double cashBalance;
  final double wealthBalance;
  final double totalAssets;
  final String currency;
  final List<TransactionRecord> recentTransactions;
  final List<SpendingSummaryItem> spendingSummary;
  final String demoTip;
}

class TransactionsData {
  const TransactionsData({
    required this.items,
    required this.spendingSummary,
  });

  factory TransactionsData.fromJson(Map<String, dynamic> json) {
    return TransactionsData(
      items: (json['items'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) =>
                TransactionRecord.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      spendingSummary: (json['spending_summary'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) =>
                SpendingSummaryItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  final List<TransactionRecord> items;
  final List<SpendingSummaryItem> spendingSummary;
}

class TransactionRecord {
  const TransactionRecord({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.isIncome,
    required this.category,
    required this.city,
    required this.createdAt,
    required this.status,
  });

  factory TransactionRecord.fromJson(Map<String, dynamic> json) {
    return TransactionRecord(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0,
      isIncome: json['is_income'] as bool? ?? false,
      category: json['category'] as String? ?? '',
      city: json['city'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
      status: json['status'] as String? ?? '',
    );
  }

  final String id;
  final String title;
  final String subtitle;
  final double amount;
  final bool isIncome;
  final String category;
  final String city;
  final String createdAt;
  final String status;
}

class SpendingSummaryItem {
  const SpendingSummaryItem({
    required this.category,
    required this.totalAmount,
  });

  factory SpendingSummaryItem.fromJson(Map<String, dynamic> json) {
    return SpendingSummaryItem(
      category: json['category'] as String? ?? '',
      totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0,
    );
  }

  final String category;
  final double totalAmount;
}

class ClientContextData {
  const ClientContextData({
    required this.sessionId,
    required this.deviceId,
    required this.platform,
    required this.currentCity,
    required this.lat,
    required this.lng,
    required this.recentPage,
    required this.lastAction,
    required this.semanticSummary,
    this.inputPauseCount,
    this.inputDurationMs,
    this.extraSignals = const <String, dynamic>{},
  });

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'session_id': sessionId,
      'device_id': deviceId,
      'platform': platform,
      'current_city': currentCity,
      'lat': lat,
      'lng': lng,
      'recent_page': recentPage,
      'last_action': lastAction,
      'semantic_summary': semanticSummary,
      if (inputPauseCount != null) 'input_pause_count': inputPauseCount,
      if (inputDurationMs != null) 'input_duration_ms': inputDurationMs,
      if (extraSignals.isNotEmpty) 'extra_signals': extraSignals,
    };
  }

  final String sessionId;
  final String deviceId;
  final String platform;
  final String currentCity;
  final double lat;
  final double lng;
  final String recentPage;
  final String lastAction;
  final String semanticSummary;
  final int? inputPauseCount;
  final int? inputDurationMs;
  final Map<String, dynamic> extraSignals;
}

class TransferPrecheckResult {
  const TransferPrecheckResult({
    required this.decision,
    required this.riskLevel,
    required this.reasons,
    required this.confirmationToken,
    required this.assistantMessage,
    required this.riskClassification,
    this.flagS = 0,
    this.gBehavior = 0,
    this.gDynamic = 0,
    this.finalRisk = 0,
    this.explainPack = const ExplainPackData.empty(),
  });

  factory TransferPrecheckResult.fromJson(Map<String, dynamic> json) {
    final RiskClassificationData classification = RiskClassificationData.fromJson(
      json['risk_classification'] as Map<String, dynamic>? ?? <String, dynamic>{},
    );
    final double flagS = (json['flag_s'] as num?)?.toDouble() ?? 0;
    final double gBehavior = (json['g_behavior'] as num?)?.toDouble() ?? 0;
    final double gDynamic = (json['g_dynamic'] as num?)?.toDouble() ?? 0;
    final double finalRisk = (json['final_risk'] as num?)?.toDouble() ?? 0;
    final List<String> reasons = (json['reasons'] as List<dynamic>? ?? <dynamic>[])
        .map((dynamic item) => item.toString())
        .toList();

    final Map<String, dynamic>? explainPackJson =
        json['explain_pack'] as Map<String, dynamic>?;
    final ExplainPackData explainPack = explainPackJson != null
        ? ExplainPackData.fromJson(explainPackJson)
        : ExplainPackData.fallbackPrecheck(
            decision: json['decision'] as String? ?? 'pass',
            riskLevel: json['risk_level'] as String? ?? 'low',
            reasons: reasons,
            riskClassification: classification,
            scoreBreakdown: RiskScoreBreakdownData(
              flagS: flagS,
              gBehavior: gBehavior,
              gDynamic: gDynamic,
              finalRisk: finalRisk,
            ),
          );

    return TransferPrecheckResult(
      decision: json['decision'] as String? ?? 'pass',
      riskLevel: json['risk_level'] as String? ?? 'low',
      reasons: reasons,
      confirmationToken: json['confirmation_token'] as String? ?? '',
      assistantMessage: json['assistant_message'] as String? ?? '',
      riskClassification: classification,
      flagS: flagS,
      gBehavior: gBehavior,
      gDynamic: gDynamic,
      finalRisk: finalRisk,
      explainPack: explainPack,
    );
  }

  final String decision;
  final String riskLevel;
  final List<String> reasons;
  final String confirmationToken;
  final String assistantMessage;
  final RiskClassificationData riskClassification;
  final double flagS;
  final double gBehavior;
  final double gDynamic;
  final double finalRisk;
  final ExplainPackData explainPack;
}

class TransferConfirmResult {
  const TransferConfirmResult({
    required this.success,
    required this.assistantMessage,
    required this.cashBalance,
    required this.wealthBalance,
    required this.totalAssets,
    required this.latestTransaction,
  });

  factory TransferConfirmResult.fromJson(Map<String, dynamic> json) {
    return TransferConfirmResult(
      success: json['success'] as bool? ?? false,
      assistantMessage: json['assistant_message'] as String? ?? '',
      cashBalance: (json['cash_balance'] as num?)?.toDouble() ?? 0,
      wealthBalance: (json['wealth_balance'] as num?)?.toDouble() ?? 0,
      totalAssets: (json['total_assets'] as num?)?.toDouble() ?? 0,
      latestTransaction: TransactionRecord.fromJson(
        json['latest_transaction'] as Map<String, dynamic>? ?? <String, dynamic>{},
      ),
    );
  }

  final bool success;
  final String assistantMessage;
  final double cashBalance;
  final double wealthBalance;
  final double totalAssets;
  final TransactionRecord latestTransaction;
}

class TransferCancelResult {
  const TransferCancelResult({
    required this.success,
    required this.status,
    required this.confirmationToken,
    required this.assistantMessage,
  });

  factory TransferCancelResult.fromJson(Map<String, dynamic> json) {
    return TransferCancelResult(
      success: json['success'] as bool? ?? false,
      status: json['status'] as String? ?? 'cancelled',
      confirmationToken: json['confirmation_token'] as String? ?? '',
      assistantMessage: json['assistant_message'] as String? ?? '',
    );
  }

  final bool success;
  final String status;
  final String confirmationToken;
  final String assistantMessage;
}

class TransferSecondaryCheckResult {
  const TransferSecondaryCheckResult({
    required this.secondaryDecision,
    required this.reasons,
    required this.finalRiskAfterSecondary,
    required this.assistantMessage,
    required this.riskClassification,
    this.explainPack = const ExplainPackData.empty(),
  });

  factory TransferSecondaryCheckResult.fromJson(Map<String, dynamic> json) {
    final RiskClassificationData classification = RiskClassificationData.fromJson(
      json['risk_classification'] as Map<String, dynamic>? ?? <String, dynamic>{},
    );
    final List<String> reasons = (json['reasons'] as List<dynamic>? ?? <dynamic>[])
        .map((dynamic item) => item.toString())
        .toList();
    final double finalRiskAfterSecondary =
        (json['final_risk_after_secondary'] as num?)?.toDouble() ?? 1.0;
    final Map<String, dynamic>? explainPackJson =
        json['explain_pack'] as Map<String, dynamic>?;
    final ExplainPackData explainPack = explainPackJson != null
        ? ExplainPackData.fromJson(explainPackJson)
        : ExplainPackData.fallbackSecondary(
            secondaryDecision:
                json['secondary_decision'] as String? ?? 'block_secondary',
            reasons: reasons,
            riskClassification: classification,
            finalRiskAfterSecondary: finalRiskAfterSecondary,
          );

    return TransferSecondaryCheckResult(
      secondaryDecision: json['secondary_decision'] as String? ?? 'block_secondary',
      reasons: reasons,
      finalRiskAfterSecondary: finalRiskAfterSecondary,
      assistantMessage: json['assistant_message'] as String? ?? '',
      riskClassification: classification,
      explainPack: explainPack,
    );
  }

  final String secondaryDecision;
  final List<String> reasons;
  final double finalRiskAfterSecondary;
  final String assistantMessage;
  final RiskClassificationData riskClassification;
  final ExplainPackData explainPack;
}

class RiskClassificationData {
  const RiskClassificationData({
    required this.riskCategory,
    required this.riskLevel,
    required this.blockHint,
    required this.matchedKeywords,
    required this.matchedScenarios,
    required this.analysis,
    required this.followUpQuestions,
    required this.suggestedReplyExamples,
  });

  factory RiskClassificationData.fromJson(Map<String, dynamic> json) {
    return RiskClassificationData(
      riskCategory: json['risk_category'] as String? ?? '正常转账',
      riskLevel: json['risk_level'] as String? ?? 'low',
      blockHint: json['block_hint'] as bool? ?? false,
      matchedKeywords: (json['matched_keywords'] as List<dynamic>? ?? <dynamic>[])
          .map((dynamic item) => item.toString())
          .toList(),
      matchedScenarios:
          (json['matched_scenarios'] as List<dynamic>? ?? <dynamic>[])
              .map((dynamic item) => item.toString())
              .toList(),
      analysis: json['analysis'] as String? ?? '',
      followUpQuestions:
          (json['follow_up_questions'] as List<dynamic>? ?? <dynamic>[])
              .map((dynamic item) => item.toString())
              .toList(),
      suggestedReplyExamples:
          (json['suggested_reply_examples'] as List<dynamic>? ?? <dynamic>[])
              .map((dynamic item) => item.toString())
              .toList(),
    );
  }

  final String riskCategory;
  final String riskLevel;
  final bool blockHint;
  final List<String> matchedKeywords;
  final List<String> matchedScenarios;
  final String analysis;
  final List<String> followUpQuestions;
  final List<String> suggestedReplyExamples;
}

class ExplainPackData {
  const ExplainPackData({
    required this.headline,
    required this.recommendedAction,
    required this.scoreBreakdown,
    required this.nodes,
  });

  const ExplainPackData.empty()
      : headline = '',
        recommendedAction = '',
        scoreBreakdown = const RiskScoreBreakdownData.empty(),
        nodes = const <ExplainNodeData>[];

  factory ExplainPackData.fromJson(Map<String, dynamic> json) {
    return ExplainPackData(
      headline: json['headline'] as String? ?? '',
      recommendedAction: json['recommended_action'] as String? ?? '',
      scoreBreakdown: RiskScoreBreakdownData.fromJson(
        json['score_breakdown'] as Map<String, dynamic>? ?? <String, dynamic>{},
      ),
      nodes: (json['nodes'] as List<dynamic>? ?? <dynamic>[])
          .map((dynamic item) => ExplainNodeData.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  factory ExplainPackData.fallbackPrecheck({
    required String decision,
    required String riskLevel,
    required List<String> reasons,
    required RiskClassificationData riskClassification,
    required RiskScoreBreakdownData scoreBreakdown,
  }) {
    final String headline = switch (decision) {
      'block' => '交易被拦截，存在高风险信号',
      'interrogate' => '交易需要补充确认',
      _ => '交易风险较低，可继续操作',
    };
    final String action = switch (decision) {
      'block' => '暂停转账并通过官方渠道核验收款方。',
      'interrogate' => '先完成二次质询，确认关系与用途后再继续。',
      _ => '请继续保持正常转账习惯，避免泄露验证码。',
    };
    final String level = _normalizeRiskLevel(riskLevel);
    return ExplainPackData(
      headline: headline,
      recommendedAction: action,
      scoreBreakdown: scoreBreakdown,
      nodes: <ExplainNodeData>[
        ExplainNodeData(
          id: 'knowledge',
          title: '知识库分类',
          level: level,
          summary: riskClassification.riskCategory,
          detail: riskClassification.analysis,
          score: scoreBreakdown.gDynamic,
        ),
        ExplainNodeData(
          id: 'risk-reasons',
          title: '触发信号',
          level: level,
          summary: reasons.isNotEmpty ? reasons.first : '未命中明显风险信号',
          detail: reasons.skip(1).take(2).join('；'),
          score: scoreBreakdown.finalRisk,
        ),
        ExplainNodeData(
          id: 'decision',
          title: '决策结论',
          level: level,
          summary: headline,
          detail: action,
          score: scoreBreakdown.finalRisk,
        ),
      ],
    );
  }

  factory ExplainPackData.fallbackSecondary({
    required String secondaryDecision,
    required List<String> reasons,
    required RiskClassificationData riskClassification,
    required double finalRiskAfterSecondary,
  }) {
    final bool blocked = secondaryDecision == 'block_secondary';
    final bool needsStop = secondaryDecision == 'interrogate';
    final String level =
        blocked
            ? 'high'
            : needsStop
            ? 'medium'
            : riskClassification.riskLevel;
    final String headline =
        blocked
            ? '二次校验未通过'
            : needsStop
            ? '二次说明未通过'
            : '二次校验通过';
    final String recommendedAction =
        blocked
            ? '建议停止转账并联系银行客服进一步核验。'
            : needsStop
            ? '当前转账不得继续确认，请关闭或取消交易。'
            : '可以继续执行转账确认。';
    return ExplainPackData(
      headline: headline,
      recommendedAction: recommendedAction,
      scoreBreakdown: RiskScoreBreakdownData(
        flagS: 0,
        gBehavior: 0,
        gDynamic: 0,
        finalRisk: finalRiskAfterSecondary,
      ),
      nodes: <ExplainNodeData>[
        ExplainNodeData(
          id: 'secondary-classification',
          title: '二次分类结果',
          level: _normalizeRiskLevel(level),
          summary: riskClassification.riskCategory,
          detail: riskClassification.analysis,
          score: finalRiskAfterSecondary,
        ),
        ExplainNodeData(
          id: 'secondary-reason',
          title: '二次判断依据',
          level: _normalizeRiskLevel(level),
          summary: reasons.isNotEmpty ? reasons.first : '模型未返回额外原因',
          detail: reasons.skip(1).take(2).join('；'),
          score: finalRiskAfterSecondary,
        ),
      ],
    );
  }

  static String _normalizeRiskLevel(String raw) {
    final String value = raw.trim().toLowerCase();
    if (value == 'high' || value == 'medium' || value == 'low') {
      return value;
    }
    return 'medium';
  }

  final String headline;
  final String recommendedAction;
  final RiskScoreBreakdownData scoreBreakdown;
  final List<ExplainNodeData> nodes;
}

class RiskScoreBreakdownData {
  const RiskScoreBreakdownData({
    required this.flagS,
    required this.gBehavior,
    required this.gDynamic,
    required this.finalRisk,
  });

  const RiskScoreBreakdownData.empty()
      : flagS = 0,
        gBehavior = 0,
        gDynamic = 0,
        finalRisk = 0;

  factory RiskScoreBreakdownData.fromJson(Map<String, dynamic> json) {
    return RiskScoreBreakdownData(
      flagS: (json['flag_s'] as num?)?.toDouble() ?? 0,
      gBehavior: (json['g_behavior'] as num?)?.toDouble() ?? 0,
      gDynamic: (json['g_dynamic'] as num?)?.toDouble() ?? 0,
      finalRisk: (json['final_risk'] as num?)?.toDouble() ?? 0,
    );
  }

  final double flagS;
  final double gBehavior;
  final double gDynamic;
  final double finalRisk;
}

class ExplainNodeData {
  const ExplainNodeData({
    required this.id,
    required this.title,
    required this.level,
    required this.summary,
    required this.detail,
    required this.score,
  });

  factory ExplainNodeData.fromJson(Map<String, dynamic> json) {
    return ExplainNodeData(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '风险节点',
      level: json['level'] as String? ?? 'medium',
      summary: json['summary'] as String? ?? '',
      detail: json['detail'] as String? ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0,
    );
  }

  final String id;
  final String title;
  final String level;
  final String summary;
  final String detail;
  final double score;
}

class ChatTurn {
  const ChatTurn({
    required this.role,
    required this.content,
  });

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'role': role,
      'content': content,
    };
  }

  final String role;
  final String content;
}

class ChatReply {
  const ChatReply({
    required this.assistantMessage,
    required this.usedTools,
    required this.suggestedActions,
  });

  factory ChatReply.fromJson(Map<String, dynamic> json) {
    return ChatReply(
      assistantMessage: json['assistant_message'] as String? ?? '',
      usedTools: (json['used_tools'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) => ToolUsageItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      suggestedActions: (json['suggested_actions'] as List<dynamic>? ?? <dynamic>[])
          .map(
            (dynamic item) =>
                SuggestedActionItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  final String assistantMessage;
  final List<ToolUsageItem> usedTools;
  final List<SuggestedActionItem> suggestedActions;
}

class ToolUsageItem {
  const ToolUsageItem({
    required this.name,
    required this.summary,
  });

  factory ToolUsageItem.fromJson(Map<String, dynamic> json) {
    return ToolUsageItem(
      name: json['name'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
    );
  }

  final String name;
  final String summary;
}

class SuggestedActionItem {
  const SuggestedActionItem({
    required this.label,
    required this.action,
  });

  factory SuggestedActionItem.fromJson(Map<String, dynamic> json) {
    return SuggestedActionItem(
      label: json['label'] as String? ?? '',
      action: json['action'] as String? ?? '',
    );
  }

  final String label;
  final String action;
}
