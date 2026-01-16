#!/usr/bin/env python3
"""Matrix Watcher v1.0 - CLI for Offline Analysis.

Commands:
- correlations: Build correlation matrix
- lag: Lag-correlation analysis
- anomalies: Anomaly summary
- clusters: Cluster analysis
- timeline: Timeline visualization
- precursors: Precursor pattern analysis
- advanced: Advanced statistical analysis (MI, FFT)
- report: Send full report to Telegram
"""

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.config import ConfigManager
from src.storage import StorageManager
from src.monitoring import TelegramBot
from src.analyzers.offline import (
    CorrelationAnalyzer,
    LagCorrelationAnalyzer,
    ClusterAnalyzer,
    PrecursorAnalyzer,
    AdvancedAnalyzer,
)


def get_telegram_bot() -> TelegramBot | None:
    """Get configured Telegram bot."""
    try:
        config = ConfigManager("config.json").load()
        tg = config.alerting.telegram
        if tg.enabled and tg.token and tg.chat_id:
            return TelegramBot(token=tg.token, chat_id=tg.chat_id, cooldown_seconds=5)
    except Exception:
        pass
    return None


def parse_date(date_str: str) -> date:
    """Parse date string to date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def cmd_correlations(args):
    """Build correlation matrix."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Building correlation matrix from {args.start_date} to {args.end_date}...")
    
    # Load data from all sensors
    df = storage.read_all_sensors(args.start_date, args.end_date)
    
    if df.empty:
        print("No data found for the specified date range.")
        return
    
    analyzer = CorrelationAnalyzer(significance_threshold=0.7)
    results = analyzer.analyze(df)
    
    # Output
    if args.output:
        results["correlation_matrix"].to_csv(args.output)
        print(f"Correlation matrix saved to {args.output}")
        
        # Save heatmap
        heatmap_path = args.output.replace(".csv", "_heatmap.png")
        analyzer.generate_heatmap(results["correlation_matrix"], heatmap_path)
    else:
        print("\nCorrelation Matrix:")
        print(results["correlation_matrix"].to_string())
    
    # Show significant correlations
    print(f"\nSignificant correlations (|r| > 0.7): {len(results['significant_pairs'])}")
    for pair in results["significant_pairs"][:20]:
        print(f"  {pair['param1']} <-> {pair['param2']}: {pair['correlation']:.3f} ({pair['direction']})")


def cmd_lag(args):
    """Lag-correlation analysis."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Running lag-correlation analysis from {args.start_date} to {args.end_date}...")
    
    df = storage.read_all_sensors(args.start_date, args.end_date)
    
    if df.empty:
        print("No data found.")
        return
    
    analyzer = LagCorrelationAnalyzer(max_lag=60, causal_threshold=5)
    results = analyzer.analyze(df)
    
    print(f"\nAnalyzed {results['total_pairs']} parameter pairs")
    print(f"Found {results['causal_count']} potential causal relationships")
    
    print("\nTop causal relationships:")
    for rel in results["causal_relationships"][:10]:
        print(f"  {rel['relationship']}")
        print(f"    Correlation: {rel['max_correlation']:.3f}, Lag: {rel['optimal_lag']}s")
    
    if args.output:
        pd.DataFrame(results["all_pairs"]).to_csv(args.output, index=False)
        print(f"\nResults saved to {args.output}")


def cmd_clusters(args):
    """Cluster analysis of anomalies."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Running cluster analysis from {args.start_date} to {args.end_date}...")
    
    anomalies = storage.read_records("anomalies", args.start_date, args.end_date)
    
    if anomalies.empty:
        print("No anomalies found.")
        return
    
    analyzer = ClusterAnalyzer(time_window=3.0, multi_source_threshold=3)
    results = analyzer.analyze(anomalies)
    
    print(f"\nTotal anomalies: {results['total_anomalies']}")
    print(f"Clusters found: {results['total_clusters']}")
    print(f"Multi-source clusters: {results['multi_source_count']}")
    
    print("\nTop clusters:")
    for cluster in results["clusters"][:10]:
        print(f"  Rank {cluster['rank']}: {cluster['anomaly_count']} anomalies from {cluster['unique_sources']} sources")
        print(f"    Sources: {', '.join(cluster['sources'])}")
        print(f"    Time span: {cluster['time_span']:.2f}s")
    
    if args.output:
        results["summary"].to_csv(args.output, index=False)
        print(f"\nSummary saved to {args.output}")


def cmd_precursors(args):
    """Precursor pattern analysis."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Running precursor analysis from {args.start_date} to {args.end_date}...")
    
    data = storage.read_all_sensors(args.start_date, args.end_date)
    anomalies = storage.read_records("anomalies", args.start_date, args.end_date)
    
    if data.empty or anomalies.empty:
        print("Insufficient data for precursor analysis.")
        return
    
    analyzer = PrecursorAnalyzer(windows=[5, 10, 30], min_frequency=0.3)
    results = analyzer.analyze(data, anomalies)
    
    print(results["report"])
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(results["report"])
        print(f"\nReport saved to {args.output}")


def cmd_advanced(args):
    """Advanced statistical analysis."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Running advanced analysis from {args.start_date} to {args.end_date}...")
    
    df = storage.read_all_sensors(args.start_date, args.end_date)
    
    if df.empty:
        print("No data found.")
        return
    
    analyzer = AdvancedAnalyzer()
    results = analyzer.analyze(df)
    
    print(f"\nParameters analyzed: {results['parameters_analyzed']}")
    print(f"Significant MI pairs: {results['significant_mi_count']}")
    print(f"Periodic parameters: {results['periodic_parameters']}")
    
    print("\nTop mutual information pairs:")
    for pair in results["significant_mi_pairs"][:10]:
        print(f"  {pair['param1']} <-> {pair['param2']}: MI={pair['mutual_information']:.4f}")
    
    if results["suspicious_periodicities"]:
        print("\nSuspicious periodicities detected:")
        for p in results["suspicious_periodicities"]:
            print(f"  {p['parameter']}:")
            for period in p["dominant_periods"]:
                if period["is_suspicious"]:
                    print(f"    Period: {period['period_hours']:.2f} hours")
    
    if args.output:
        results["mutual_information_matrix"].to_csv(args.output)
        print(f"\nMI matrix saved to {args.output}")


def cmd_anomalies(args):
    """Show anomaly summary."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Loading anomalies from {args.start_date} to {args.end_date}...")
    
    df = storage.read_records("anomalies", args.start_date, args.end_date)
    
    if df.empty:
        print("No anomalies found.")
        return
    
    print(f"\nTotal anomalies: {len(df)}")
    
    if "sensor_source" in df.columns:
        print("\nAnomalies by sensor:")
        print(df["sensor_source"].value_counts().to_string())
    
    if "parameter" in df.columns:
        print("\nAnomalies by parameter:")
        print(df["parameter"].value_counts().head(10).to_string())
    
    if args.output:
        df.to_csv(args.output, index=False)
        print(f"\nAnomalies saved to {args.output}")


def cmd_timeline(args):
    """Show timeline of events."""
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Loading data from {args.start_date} to {args.end_date}...")
    
    sensors = storage.get_all_sensors()
    
    print("\nData availability:")
    for sensor in sensors:
        df = storage.read_records(sensor, args.start_date, args.end_date)
        if not df.empty:
            print(f"  {sensor}: {len(df)} records")


async def cmd_report_async(args):
    """Send full analysis report to Telegram."""
    bot = get_telegram_bot()
    if not bot:
        print("❌ Telegram не настроен. Запустите: python3 setup_telegram.py")
        return
    
    storage = StorageManager(base_path=args.logs_path)
    
    print(f"Анализ данных с {args.start_date} по {args.end_date}...")
    
    # Load data
    df = storage.read_all_sensors(args.start_date, args.end_date)
    anomalies = storage.read_records("anomalies", args.start_date, args.end_date)
    
    if df.empty:
        print("Нет данных для анализа.")
        await bot.send_message("📊 <b>Отчёт</b>\n\nНет данных для анализа за указанный период.")
        await bot.close()
        return
    
    # 1. Correlations
    print("Анализ корреляций...")
    corr_analyzer = CorrelationAnalyzer(significance_threshold=0.7)
    corr_results = corr_analyzer.analyze(df)
    
    if corr_results["significant_pairs"]:
        for pair in corr_results["significant_pairs"][:5]:
            await bot.notify_correlation(
                param1=pair["param1"],
                param2=pair["param2"],
                correlation=pair["correlation"]
            )
            await asyncio.sleep(0.5)  # Rate limiting
    
    # 2. Lag correlations
    print("Анализ lag-корреляций...")
    lag_analyzer = LagCorrelationAnalyzer(max_lag=60, causal_threshold=5)
    lag_results = lag_analyzer.analyze(df)
    
    if lag_results["causal_relationships"]:
        for rel in lag_results["causal_relationships"][:3]:
            await bot.notify_lag_correlation(
                param1=rel["param1"],
                param2=rel["param2"],
                lag_seconds=rel["optimal_lag"],
                correlation=rel["max_correlation"],
                is_causal=True
            )
            await asyncio.sleep(0.5)
    
    # 3. Clusters
    if not anomalies.empty:
        print("Анализ кластеров...")
        cluster_analyzer = ClusterAnalyzer(time_window=3.0, multi_source_threshold=3)
        cluster_results = cluster_analyzer.analyze(anomalies)
        
        for cluster in cluster_results["clusters"][:3]:
            if cluster["unique_sources"] >= 3:
                await bot.notify_cluster(
                    sources=cluster["sources"],
                    anomaly_count=cluster["anomaly_count"],
                    time_span_seconds=cluster["time_span"]
                )
                await asyncio.sleep(0.5)
    
    # 4. Precursors
    if not anomalies.empty:
        print("Анализ предвестников...")
        prec_analyzer = PrecursorAnalyzer(windows=[5, 10, 30], min_frequency=0.3)
        prec_results = prec_analyzer.analyze(df, anomalies)
        
        for pattern in prec_results.get("patterns", [])[:3]:
            await bot.notify_precursor(
                precursor_param=pattern.get("precursor", "unknown"),
                target_param=pattern.get("target", "unknown"),
                lead_time_seconds=pattern.get("lead_time", 0),
                frequency=pattern.get("frequency", 0),
                confidence=pattern.get("confidence", 0)
            )
            await asyncio.sleep(0.5)
    
    # 5. Advanced (FFT)
    print("Анализ периодичности...")
    adv_analyzer = AdvancedAnalyzer()
    adv_results = adv_analyzer.analyze(df)
    
    for p in adv_results.get("suspicious_periodicities", [])[:3]:
        for period in p.get("dominant_periods", []):
            if period.get("is_suspicious"):
                await bot.notify_periodicity(
                    parameter=p["parameter"],
                    period_seconds=period["period_hours"] * 3600,
                    strength=period.get("strength", 0.5)
                )
                await asyncio.sleep(0.5)
    
    # Summary
    anomaly_count = len(anomalies) if not anomalies.empty else 0
    await bot.send_daily_summary(
        anomaly_count=anomaly_count,
        correlation_count=len(corr_results["significant_pairs"]),
        cluster_count=cluster_results["multi_source_count"] if not anomalies.empty else 0
    )
    
    await bot.close()
    print("✅ Отчёт отправлен в Telegram!")


def cmd_report(args):
    """Send report to Telegram (sync wrapper)."""
    asyncio.run(cmd_report_async(args))


def main():
    parser = argparse.ArgumentParser(
        description="Matrix Watcher - Offline Analysis CLI"
    )
    parser.add_argument(
        "--logs-path", default="logs",
        help="Path to logs directory"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Analysis command")
    
    # Common arguments
    def add_common_args(p):
        p.add_argument(
            "--start-date", type=parse_date,
            default=date.today() - timedelta(days=7),
            help="Start date (YYYY-MM-DD)"
        )
        p.add_argument(
            "--end-date", type=parse_date,
            default=date.today(),
            help="End date (YYYY-MM-DD)"
        )
        p.add_argument(
            "--output", "-o",
            help="Output file path"
        )
    
    # Correlations
    p_corr = subparsers.add_parser("correlations", help="Build correlation matrix")
    add_common_args(p_corr)
    
    # Lag correlations
    p_lag = subparsers.add_parser("lag", help="Lag-correlation analysis")
    add_common_args(p_lag)
    
    # Anomalies
    p_anom = subparsers.add_parser("anomalies", help="Anomaly summary")
    add_common_args(p_anom)
    
    # Clusters
    p_clust = subparsers.add_parser("clusters", help="Cluster analysis")
    add_common_args(p_clust)
    
    # Precursors
    p_prec = subparsers.add_parser("precursors", help="Precursor pattern analysis")
    add_common_args(p_prec)
    
    # Advanced
    p_adv = subparsers.add_parser("advanced", help="Advanced statistical analysis")
    add_common_args(p_adv)
    
    # Timeline
    p_time = subparsers.add_parser("timeline", help="Timeline visualization")
    add_common_args(p_time)
    
    # Report to Telegram
    p_report = subparsers.add_parser("report", help="Send full report to Telegram")
    add_common_args(p_report)
    
    args = parser.parse_args()
    
    if args.command == "correlations":
        cmd_correlations(args)
    elif args.command == "lag":
        cmd_lag(args)
    elif args.command == "anomalies":
        cmd_anomalies(args)
    elif args.command == "clusters":
        cmd_clusters(args)
    elif args.command == "precursors":
        cmd_precursors(args)
    elif args.command == "advanced":
        cmd_advanced(args)
    elif args.command == "timeline":
        cmd_timeline(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
