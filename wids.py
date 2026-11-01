"""Educational WIDS: train/test on labelled Wi-Fi frame CSV; replay alerts.
All traffic generation is SYNTHETIC and does not transmit wireless frames.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import GroupShuffleSplit
import joblib

ROOT = Path(__file__).resolve().parent
FEATURES = ['frames_per_second', 'deauth_per_second', 'deauth_ratio', 'mean_signal_dbm', 'management_ratio']
REQUIRED = ['timestamp', 'src_mac', 'frame_type', 'subtype', 'rssi_dbm', 'label', 'session_id']


def generate(seed=42, sessions_per_class=45):
    """Make reproducible, explicitly synthetic 802.11-like frame records."""
    rng = np.random.default_rng(seed)
    records = []
    base = pd.Timestamp('2026-10-01T09:00:00Z')
    for attack in (0, 1):
        for s in range(sessions_per_class):
            session = f'{"attack" if attack else "normal"}_{s:03d}'
            src = f'02:{attack:02x}:{s:02x}:{(s*3)%256:02x}:{(s*7)%256:02x}:{(s*11)%256:02x}'
            start = base + pd.Timedelta(minutes=(attack * sessions_per_class + s) * 2)
            signal = float(rng.uniform(-78, -38))
            for sec in range(12):
                # Attack session has 1-2 normal seconds before its flood.
                flood = attack and sec >= 2
                deauth_n = int(rng.integers(24, 75)) if flood else int(rng.choice([0, 0, 0, 1, 2]))
                other_n = int(rng.integers(4, 22))
                entries = [('management', 'deauth')] * deauth_n
                for _ in range(other_n):
                    kind = rng.choice(['data', 'management', 'control'], p=[.68, .22, .10])
                    subtype = ('data' if kind == 'data' else ('beacon' if kind == 'management' else 'ack'))
                    entries.append((kind, subtype))
                for kind, subtype in entries:
                    t = start + pd.Timedelta(seconds=sec + float(rng.uniform(0, .999)))
                    records.append((t.isoformat(), src, kind, subtype, round(signal + rng.normal(0, 3), 1),
                                    int(flood), session))
    df = pd.DataFrame(records, columns=REQUIRED)
    df = df.sort_values('timestamp').reset_index(drop=True)
    path = ROOT / 'data' / 'synthetic_wifi_frames.csv'
    path.parent.mkdir(exist_ok=True)
    df.to_csv(path, index=False)
    return path, len(df)


def windows(csv_path):
    df = pd.read_csv(csv_path)
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f'Missing CSV fields: {sorted(missing)}. See README.md')
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='raise')
    df['rssi_dbm'] = pd.to_numeric(df['rssi_dbm'], errors='coerce')
    df['label'] = pd.to_numeric(df['label'], errors='raise').astype(int)
    if not df['label'].isin([0, 1]).all():
        raise ValueError('Labels must be 0 normal and 1 deauth flood.')
    df['second'] = df['timestamp'].dt.floor('s')
    df['is_deauth'] = ((df['frame_type'].astype(str).str.lower() == 'management') &
                       (df['subtype'].astype(str).str.lower() == 'deauth')).astype(int)
    df['is_management'] = (df['frame_type'].astype(str).str.lower() == 'management').astype(int)
    g = df.groupby(['session_id', 'src_mac', 'second'], as_index=False)
    w = g.agg(frames_per_second=('src_mac', 'size'), deauth_per_second=('is_deauth', 'sum'),
              mean_signal_dbm=('rssi_dbm', 'mean'), management_count=('is_management', 'sum'),
              label=('label', 'max'))
    # No signal in some datasets. Represent missing RSSI with fixed -90 dBm for demo only.
    w['mean_signal_dbm'] = w['mean_signal_dbm'].fillna(-90)
    w['deauth_ratio'] = w['deauth_per_second'] / w['frames_per_second']
    w['management_ratio'] = w['management_count'] / w['frames_per_second']
    return w.sort_values(['second', 'src_mac']).reset_index(drop=True)


def train(csv_path):
    w = windows(csv_path)
    groups = w['session_id']
    splitter = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42)
    tr, te = next(splitter.split(w[FEATURES], w['label'], groups))
    model = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42,
                                   class_weight='balanced', n_jobs=-1)
    model.fit(w.iloc[tr][FEATURES], w.iloc[tr]['label'])
    y_true = w.iloc[te]['label']
    y_pred = model.predict(w.iloc[te][FEATURES])
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    acc = accuracy_score(y_true, y_pred)
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(cm, display_labels=['Normal', 'Deauth flood']).plot(ax=ax, cmap='Blues', values_format='d', colorbar=False)
    fig.suptitle('WIDS confusion matrix — held-out sessions')
    fig.tight_layout()
    fig.savefig(out / 'confusion_matrix.png', dpi=200)
    plt.close(fig)
    report = classification_report(y_true, y_pred, labels=[0, 1], target_names=['Normal', 'Deauth flood'], zero_division=0)
    (out / 'classification_report.txt').write_text(report, encoding='utf-8')
    info = {'accuracy': round(float(acc), 4), 'confusion_matrix': cm.tolist(),
            'train_windows': len(tr), 'test_windows': len(te),
            'train_sessions': int(groups.iloc[tr].nunique()),
            'test_sessions': int(groups.iloc[te].nunique()),
            'dataset': str(csv_path), 'features': FEATURES,
            'note': 'Results from synthetic traffic ONLY unless replaced by a real labelled dataset.'}
    (out / 'metrics.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    joblib.dump({'model': model, 'features': FEATURES}, ROOT / 'wids_model.joblib')
    print(f'Train windows: {len(tr)} | Test windows: {len(te)} | Accuracy: {acc:.2%}')
    print('Confusion matrix [[TN, FP], [FN, TP]]:', cm.tolist())
    print(report)
    print('Saved results/confusion_matrix.png, results/metrics.json, wids_model.joblib')


def demo(csv_path, limit=45):
    bundle = joblib.load(ROOT / 'wids_model.joblib')
    w = windows(csv_path)
    # Display a handful of normal windows then suspicious windows to visibly demonstrate detection.
    regular = w[w.deauth_per_second <= 2].head(max(6, limit // 3))
    suspicious = w[w.deauth_per_second >= 20].head(max(6, limit - len(regular)))
    sample = pd.concat([regular, suspicious]).head(limit)
    log = ROOT / 'results' / 'alerts.csv'
    log.parent.mkdir(exist_ok=True)
    alerts = []
    for _, r in sample.iterrows():
        pred = int(bundle['model'].predict(pd.DataFrame([r[bundle['features']]], columns=bundle['features']))[0])
        label = 'ALERT: DEAUTH FLOOD' if pred else 'NORMAL'
        print(f'{r["second"]} | {r["src_mac"]} | deauth/s={int(r["deauth_per_second"]):3d} | {label}')
        if pred:
            alerts.append({'timestamp': str(r['second']), 'src_mac': r['src_mac'],
                           'deauth_per_second': int(r['deauth_per_second']), 'alert': label})
    pd.DataFrame(alerts, columns=['timestamp', 'src_mac', 'deauth_per_second', 'alert']).to_csv(log, index=False)
    print(f'Logged {len(alerts)} alert(s) to {log}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Windows-friendly offline WIDS prototype')
    parser.add_argument('command', choices=['generate', 'train', 'demo'])
    parser.add_argument('--csv', default=str(ROOT / 'data' / 'synthetic_wifi_frames.csv'))
    parser.add_argument('--limit', type=int, default=45)
    args = parser.parse_args()
    if args.command == 'generate':
        p, count = generate()
        print(f'Generated {count:,} SYNTHETIC frames: {p}')
    elif args.command == 'train':
        train(args.csv)
    else:
        demo(args.csv, args.limit)
