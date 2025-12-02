"""
Results visualization
"""
import os
import sys
from typing import Dict, Any, List
import json

# Matplotlib/Seaborn imports with error handling
try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import seaborn as sns
    import pandas as pd
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("[WARNING] Visualization libraries not available. Install: pip install matplotlib seaborn pandas")

from ..core.config import config


class ResultsVisualizer:
    """평가 결과 시각화"""
    
    def __init__(self, output_dir: str = None):
        """
        시각화 초기화
        
        Args:
            output_dir: 시각화 결과 저장 디렉토리
        """
        if not VISUALIZATION_AVAILABLE:
            raise ImportError("Visualization requires: matplotlib, seaborn, pandas")
        
        self.output_dir = output_dir or config.eval_visualizations_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 한글 폰트 설정
        self._setup_korean_font()
        
        # Seaborn 스타일
        sns.set_style("whitegrid")
        sns.set_palette("husl")
    
    def _setup_korean_font(self):
        """한글 폰트 설정"""
        if sys.platform == 'win32':
            font_names = ['Malgun Gothic', 'NanumGothic', 'Gulim']
            for font_name in font_names:
                try:
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False
                    return
                except:
                    continue
        plt.rcParams['axes.unicode_minus'] = False
    
    def load_results(self, results_file: str) -> Dict[str, Any]:
        """평가 결과 로드"""
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_all_visualizations(self, results_file: str):
        """모든 시각화 생성"""
        data = self.load_results(results_file)
        summary = data['summary']
        results = data['detailed_results']
        
        print("\n[시각화 생성 중...]")
        
        self.plot_overall_metrics(summary)
        self.plot_score_distributions(results)
        self.plot_hit_rates_comparison(summary)
        self.plot_comprehensive_report(results)
        
        print(f"\n[OK] 시각화 완료: {self.output_dir}")
    
    def plot_overall_metrics(self, summary: Dict[str, Any]):
        """전체 성능 지표 바차트"""
        metrics = {
            'Retrieval\nHit Rate': summary['retrieval_hit_rate'],
            'Semantic\nSimilarity': summary['semantic_similarity_avg'],
            'Similarity\nHit Rate': summary['similarity_hit_rate'],
            'Judge Score\n(normalized)': summary['judge_score_avg'] / 2.0,
            'Keyword\nHit Rate': summary['keyword_hit_rate']
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(metrics.keys(), metrics.values(), 
                     color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2%}',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_ylabel('Score / Rate', fontsize=12)
        ax.set_title('RAG Overall Performance', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1.1)
        ax.axhline(y=0.75, color='red', linestyle='--', alpha=0.5, label='Target (75%)')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'overall_metrics.png'), dpi=300, bbox_inches='tight')
        plt.close()
        print("[OK] overall_metrics.png")
    
    def plot_score_distributions(self, results: List[Dict[str, Any]]):
        """점수 분포 히스토그램"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Semantic Similarity
        similarities = [r['semantic_similarity'] for r in results]
        axes[0, 0].hist(similarities, bins=20, color='#4ECDC4', edgecolor='black', alpha=0.7)
        axes[0, 0].axvline(x=0.75, color='red', linestyle='--')
        axes[0, 0].set_title('Semantic Similarity')
        axes[0, 0].set_xlabel('Similarity')
        
        # Judge Score
        judge_scores = [r['judge_score'] for r in results]
        score_counts = pd.Series(judge_scores).value_counts().sort_index()
        axes[0, 1].bar(score_counts.index, score_counts.values, color=['#FF6B6B', '#FFA07A', '#98D8C8'])
        axes[0, 1].set_title('Judge Score Distribution')
        axes[0, 1].set_xticks([0, 1, 2])
        
        # Keyword Count
        keyword_counts = [r['keyword_count'] for r in results]
        axes[1, 0].hist(keyword_counts, bins=range(0, max(keyword_counts)+2), 
                       color='#45B7D1', edgecolor='black', alpha=0.7)
        axes[1, 0].set_title('Keyword Hit Count')
        
        # Retrieved Chunks
        chunk_counts = [r['num_retrieved_chunks'] for r in results]
        axes[1, 1].hist(chunk_counts, bins=range(0, max(chunk_counts)+2), 
                       color='#FFA07A', edgecolor='black', alpha=0.7)
        axes[1, 1].set_title('Retrieved Chunks')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'score_distributions.png'), dpi=300, bbox_inches='tight')
        plt.close()
        print("[OK] score_distributions.png")
    
    def plot_hit_rates_comparison(self, summary: Dict[str, Any]):
        """Hit Rate 비교 파이차트"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        metrics = [
            ('Retrieval Hit', summary['retrieval_hit_count'], summary['total_questions']),
            ('Similarity Hit', summary['similarity_hit_count'], summary['total_questions']),
            ('Keyword Hit', summary['keyword_hit_count'], summary['total_questions'])
        ]
        
        for idx, (title, hit_count, total) in enumerate(metrics):
            miss_count = total - hit_count
            sizes = [hit_count, miss_count]
            labels = [f'Hit ({hit_count})', f'Miss ({miss_count})']
            
            axes[idx].pie(sizes, labels=labels, colors=['#98D8C8', '#FFE5E5'], 
                         autopct='%1.1f%%', startangle=90)
            axes[idx].set_title(f'{title}\n({hit_count}/{total})', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'hit_rates_comparison.png'), dpi=300, bbox_inches='tight')
        plt.close()
        print("[OK] hit_rates_comparison.png")
    
    def plot_comprehensive_report(self, results: List[Dict[str, Any]]):
        """종합 리포트"""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        df = pd.DataFrame(results)
        
        # 전체 지표
        ax1 = fig.add_subplot(gs[0, :])
        metrics = {
            'Retrieval': df['retrieval_hit'].mean(),
            'Similarity': df['semantic_similarity'].mean(),
            'Judge': df['judge_score'].mean() / 2.0,
            'Keyword': df['keyword_hit'].mean()
        }
        bars = ax1.barh(list(metrics.keys()), list(metrics.values()))
        ax1.set_xlim(0, 1.1)
        ax1.set_title('Overall Metrics', fontweight='bold')
        
        # 성능 추이
        ax2 = fig.add_subplot(gs[1, :])
        x = range(min(30, len(df)))
        sample_df = df.iloc[:30]
        ax2.plot(x, sample_df['semantic_similarity'], marker='o', label='Similarity')
        ax2.plot(x, sample_df['judge_score'] / 2.0, marker='s', label='Judge')
        ax2.set_title('Performance Trend (First 30)', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        fig.suptitle('RAG Comprehensive Report', fontsize=16, fontweight='bold')
        
        plt.savefig(os.path.join(self.output_dir, 'comprehensive_report.png'), dpi=300, bbox_inches='tight')
        plt.close()
        print("[OK] comprehensive_report.png")
