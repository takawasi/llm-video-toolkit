"""コメントログ解析: 急増箇所・特定ワード検出"""
import json
import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional


def load_comment_log(log_path: str) -> list[dict]:
    """コメントログ読み込み

    対応形式:
    - JSON: [{'time': 123.4, 'text': '草', 'user': 'xxx'}, ...]
    - CSV: time,text,user のヘッダー付き

    Args:
        log_path: コメントログファイルパス

    Returns:
        [{'time': float, 'text': str, 'user': str}, ...]
    """
    path = Path(log_path)

    if path.suffix.lower() == '.json':
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # time を float に変換
            for item in data:
                if 'time' in item:
                    item['time'] = float(item['time'])
            return data

    elif path.suffix.lower() == '.csv':
        comments = []
        with open(log_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                comments.append({
                    'time': float(row.get('time', 0)),
                    'text': row.get('text', ''),
                    'user': row.get('user', '')
                })
        return comments

    else:
        raise ValueError(f"Unsupported format: {path.suffix}")


def detect_comment_spikes(comments: list[dict],
                          window_sec: int = 30,
                          threshold_ratio: float = 2.0) -> list[dict]:
    """コメント急増箇所を検出

    時間帯ごとのコメント数を集計し、平均の threshold_ratio 倍以上の
    箇所を「スパイク」として返す。

    Args:
        comments: コメントリスト
        window_sec: 集計ウィンドウ（秒）
        threshold_ratio: 平均の何倍でスパイク判定

    Returns:
        [{'time': float, 'type': 'comment_spike', 'count': int, 'avg': float}, ...]
    """
    if not comments:
        return []

    # 時間帯ごとにコメント数を集計
    buckets = defaultdict(int)
    for c in comments:
        bucket = int(c['time'] // window_sec)
        buckets[bucket] += 1

    if not buckets:
        return []

    # 平均コメント数
    avg_count = sum(buckets.values()) / len(buckets)

    # スパイク検出
    spikes = []
    for bucket, count in buckets.items():
        if count > avg_count * threshold_ratio:
            spikes.append({
                'time': bucket * window_sec + window_sec / 2,  # ウィンドウの中央
                'type': 'comment_spike',
                'count': count,
                'avg': avg_count,
                'score': count / avg_count  # 平均比をスコアに
            })

    return sorted(spikes, key=lambda x: x['score'], reverse=True)


def detect_keywords(comments: list[dict],
                    keywords: Optional[list[str]] = None) -> list[dict]:
    """特定キーワードを含むコメントの時刻を抽出

    Args:
        comments: コメントリスト
        keywords: 検出対象キーワード（None時はデフォルト）

    Returns:
        [{'time': float, 'type': 'keyword_hit', 'keyword': str, 'text': str}, ...]
    """
    if keywords is None:
        # 配信で盛り上がりを示すキーワード
        keywords = [
            '草', 'www', 'ｗｗ', 'ww',
            '神', 'かみ', 'カミ',
            'すご', 'スゴ', 'すげ', 'スゲ',
            'やば', 'ヤバ',
            'ワロタ', 'わろた', 'ワロ',
            '!?', '！？', '?!', '？！',
            'えぇ', 'ええ', 'えー',
            'うわ', 'ウワ',
            'きた', 'キタ', 'kita',
            '888', 'パチパチ', 'ぱちぱち'
        ]

    hits = []
    for c in comments:
        text = c.get('text', '')
        for kw in keywords:
            if kw.lower() in text.lower():
                hits.append({
                    'time': c['time'],
                    'type': 'keyword_hit',
                    'keyword': kw,
                    'text': text,
                    'score': 0.5  # キーワードヒットは控えめスコア
                })
                break  # 1コメントにつき1ヒットまで

    return hits


def detect_user_reactions(comments: list[dict],
                          window_sec: int = 10,
                          min_unique_users: int = 5) -> list[dict]:
    """短時間に多数のユニークユーザーが反応した箇所を検出

    同じ人が連投してるのではなく、複数人が反応してる箇所を重視。

    Args:
        comments: コメントリスト
        window_sec: 集計ウィンドウ（秒）
        min_unique_users: 最小ユニークユーザー数

    Returns:
        [{'time': float, 'type': 'user_reaction', 'unique_users': int}, ...]
    """
    if not comments:
        return []

    # 時間帯ごとにユニークユーザーを集計
    buckets = defaultdict(set)
    for c in comments:
        bucket = int(c['time'] // window_sec)
        user = c.get('user', 'anonymous')
        buckets[bucket].add(user)

    reactions = []
    for bucket, users in buckets.items():
        if len(users) >= min_unique_users:
            reactions.append({
                'time': bucket * window_sec + window_sec / 2,
                'type': 'user_reaction',
                'unique_users': len(users),
                'score': len(users) / min_unique_users  # ユーザー数比をスコアに
            })

    return sorted(reactions, key=lambda x: x['score'], reverse=True)


def analyze_comments(log_path: str) -> list[dict]:
    """メイン解析: コメントログから盛り上がり箇所を検出

    Args:
        log_path: コメントログファイルパス

    Returns:
        検出されたイベントのリスト（スコア付き）
    """
    comments = load_comment_log(log_path)

    # 各種検出
    spikes = detect_comment_spikes(comments)
    keywords = detect_keywords(comments)
    reactions = detect_user_reactions(comments)

    # 統合（スパイクとユーザー反応を優先）
    events = []
    events.extend(spikes[:10])      # スパイク上位10件
    events.extend(reactions[:10])   # ユーザー反応上位10件
    events.extend(keywords[:20])    # キーワード上位20件

    return sorted(events, key=lambda x: x.get('score', 0), reverse=True)
