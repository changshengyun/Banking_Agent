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
  Future<TransferConfirmResult> confirmTransfer(String confirmationToken);
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
      userName: json['user_name'] as String? ?? 'Demo User',
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
}

class TransferPrecheckResult {
  const TransferPrecheckResult({
    required this.decision,
    required this.riskLevel,
    required this.reasons,
    required this.confirmationToken,
    required this.assistantMessage,
  });

  factory TransferPrecheckResult.fromJson(Map<String, dynamic> json) {
    return TransferPrecheckResult(
      decision: json['decision'] as String? ?? 'pass',
      riskLevel: json['risk_level'] as String? ?? 'low',
      reasons: (json['reasons'] as List<dynamic>? ?? <dynamic>[])
          .map((dynamic item) => item.toString())
          .toList(),
      confirmationToken: json['confirmation_token'] as String? ?? '',
      assistantMessage: json['assistant_message'] as String? ?? '',
    );
  }

  final String decision;
  final String riskLevel;
  final List<String> reasons;
  final String confirmationToken;
  final String assistantMessage;
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
