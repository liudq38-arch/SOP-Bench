from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import math

from impact_qa.common import TYPES


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError('non_numeric_time')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('non_finite_time')
    return result


def normalize_segments(question, group):
    scope = question.get('scope') or {}
    fps = number(group['fps'])
    if fps <= 0:
        raise ValueError('invalid_fps')
    clip_start = number(group['start_frame']) / fps
    clip_duration = (number(group['end_frame_exclusive'])-number(group['start_frame'])) / fps
    if clip_duration <= 0:
        raise ValueError('invalid_clip_duration')
    source = 'explicit_target_segments'
    if 'target_segments' in scope:
        raw = scope['target_segments']
        if not isinstance(raw, list):
            raise ValueError('target_segments_not_array')
    elif 'playback_interval_s' in scope:
        raw = [{'interval': scope['playback_interval_s'], 'time_basis': 'clip', 'unit': 'seconds'}]
        source = 'scope.playback_interval_s'
    elif 'source_interval_s' in scope:
        raw = [{'interval': scope['source_interval_s'], 'time_basis': 'trial', 'unit': 'seconds'}]
        source = 'scope.source_interval_s'
    else:
        return [], []
    result, issues = [], []
    for index, row in enumerate(raw):
        try:
            interval = row.get('interval') if isinstance(row, dict) else None
            if not isinstance(interval, list) or len(interval) != 2:
                raise ValueError('segment_requires_two_endpoints')
            a, b = map(number, interval)
            duration = b-a
            basis, unit = row.get('time_basis'), row.get('unit', 'seconds')
            if unit == 'frames':
                if a != int(a) or b != int(b):
                    raise ValueError('non_integer_frame')
                segment_fps = number(row.get('fps', group['fps']))
                if segment_fps <= 0:
                    raise ValueError('invalid_segment_fps')
                a, b = a/segment_fps, b/segment_fps
                duration = duration/segment_fps
            elif unit != 'seconds':
                raise ValueError('unknown_time_unit')
            if basis == 'trial':
                a, b = a-clip_start, b-clip_start
            elif basis != 'clip':
                raise ValueError('unknown_time_basis')
            calibration = None
            if len(raw) == 1 and source != 'explicit_target_segments':
                events = [e for e in group.get('events', []) if e['event_id'] == question.get('question_id')]
                if len(events) == 1:
                    event = events[0]
                    exact_a = (number(event['start_frame'])-number(group['start_frame']))/fps
                    exact_b = (number(event['end_frame_exclusive'])-number(group['start_frame']))/fps
                    if abs(a-exact_a) > Decimal('0.000001') or abs(b-exact_b) > Decimal('0.000001'):
                        raise ValueError('question_event_time_mismatch')
                    a, b = exact_a, exact_b
                    duration = (number(event['end_frame_exclusive'])-number(event['start_frame']))/fps
                    calibration = dict(source='matching_group_event_frame_bounds', start_frame=event['start_frame'], end_frame_exclusive=event['end_frame_exclusive'])
            if b <= a:
                raise ValueError('non_positive_duration')
            entry = dict(segment_id=f"{question.get('question_id','unknown')}:s{index:02d}", index=index, start_s=float(a), end_s=float(b), duration_s=float(duration), duration_decimal=str(duration), source_start_s=float(a+clip_start), source_end_s=float(b+clip_start), interval_source=source, frame_calibration=calibration)
            result.append(entry)
            if a < 0 or b > clip_duration:
                issues.append(dict(segment_index=index, reason='out_of_range', detail='target_outside_clip'))
        except (ValueError, TypeError, InvalidOperation, KeyError, OverflowError) as exc:
            issues.append(dict(segment_index=index, reason='invalid', detail=str(exc)))
    return result, issues


def filter_question(question, group, threshold=1.5):
    try:
        segments, issues = normalize_segments(question, group)
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        segments, issues = [], [dict(reason='invalid', detail=str(exc))]
    if not segments and not issues:
        issues.append(dict(reason='no_segment', detail='no_target_interval'))
    for segment in segments:
        if Decimal(segment['duration_decimal']) < Decimal(str(threshold)):
            issues.append(dict(segment_index=segment['index'], reason='too_short', detail='duration_strictly_below_threshold'))
    priority = {'invalid': 0, 'out_of_range': 1, 'no_segment': 2, 'too_short': 3}
    reason = min(issues, key=lambda x: priority[x['reason']])['reason'] if issues else None
    return dict(status='discarded' if issues else 'kept', discard_reason=reason, issues=issues, target_segments=segments, threshold_s=threshold, all_segments_must_pass=True, time_basis='clip_seconds_half_open', minimum_duration_s=min((s['duration_s'] for s in segments), default=None))


def gt_types(question):
    return [TYPES[ord(x)-66] for x in question.get('GT_option_ids', []) if isinstance(x, str) and len(x) == 1 and 'B' <= x <= 'G']


def summarize(rows):
    types, trials, origins = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    reasons = Counter()
    for q in rows:
        kept = q['filter']['status'] == 'kept'
        reasons.update([q['filter']['discard_reason']] if not kept else [])
        for key in gt_types(q) or ['no_GT_anomaly']:
            types[key]['total'] += 1; types[key]['kept'] += kept
        for target, key in [(trials, q.get('trial_id','unknown')), (origins,q.get('origin','unknown'))]:
            target[key]['total'] += 1; target[key]['kept'] += kept
    def rates(table):
        return {k:dict(total=v['total'], kept=v['kept'], discarded=v['total']-v['kept'], retention_rate=v['kept']/v['total']) for k,v in sorted(table.items())}
    total = len(rows); kept = sum(q['filter']['status']=='kept' for q in rows)
    type_rates = rates(types)
    gt_total = sum(bool(gt_types(q)) for q in rows)
    gt_kept = sum(bool(gt_types(q)) and q['filter']['status']=='kept' for q in rows)
    baseline = gt_kept/gt_total if gt_total else 0
    flags=[]
    for t,s in type_rates.items():
        if t == 'no_GT_anomaly':
            continue
        others_total=sum(bool(gt_types(q)) and t not in gt_types(q) for q in rows)
        others_kept=sum(bool(gt_types(q)) and t not in gt_types(q) and q['filter']['status']=='kept' for q in rows)
        other_rate=others_kept/others_total if others_total else 0
        pooled=(s['kept']+others_kept)/(s['total']+others_total) if others_total else 0
        se=math.sqrt(pooled*(1-pooled)*(1/s['total']+1/others_total)) if others_total else 0
        z=(s['retention_rate']-other_rate)/se if se else 0
        p=math.erfc(abs(z)/math.sqrt(2))
        s.update(other_types_retention_rate=other_rate, gap_vs_others_pp=(s['retention_rate']-other_rate)*100, approximate_two_sided_p=p)
        if s['retention_rate'] < other_rate-.10:
            flags.append(dict(type=t, gap_pp=s['gap_vs_others_pp'], statistically_flagged_bonferroni=p<.05/6, p_approx=p))
    return dict(total=total, kept=kept, discarded=total-kept, discard_reasons=dict(reasons), by_gt_type=type_rates, by_trial=rates(trials), by_origin=rates(origins), gt_retention_rate=baseline, low_retention_flags=flags, type_counting='multi-label, each type counts every associated question; no_GT_anomaly reported separately', significance_note='practical flag >=10 percentage points below questions without that type; exploratory two-proportion normal approximation with Bonferroni 6, not cluster-adjusted by trial')
