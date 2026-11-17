#!/usr/bin/env python3
"""Verify the startup current-loss correction against saved C3 outputs.

Run from the complete manuscript supplement after audit_analysis.py. Re-executes
only C3 cells, since C0--C2 cannot enter the corrected consistency branch. The
saved original and sensitivity results are never overwritten.
"""
import csv,json,math,sys
from pathlib import Path
from dataclasses import replace
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'iot-digital-twin-reproducibility-main/scripts'))
from dt_sync_sim import simulate,PARAMS

def read(name):
    with (root/'results'/name).open() as f:return list(csv.DictReader(f))

def different(a,b):
    try:
        x,y=float(a),float(b)
        return not ((math.isnan(x) and math.isnan(y)) or x==y or (math.isfinite(x) and math.isfinite(y) and abs(x-y)<=1e-12))
    except (ValueError,TypeError):return str(a)!=str(b)

changes=[];counts={}
for filename in ['simulation_runs.csv','sensitivity_runs.csv']:
    selected=[r for r in read(filename) if r['config']=='C3'];counts[filename]=len(selected)
    for old in selected:
        kwargs={}
        if filename=='sensitivity_runs.csv':
            scale=float(old['noise_scale']);p=replace(PARAMS,D=float(old['D']),SIGMA_V=PARAMS.SIGMA_V*scale,SIGMA_I=PARAMS.SIGMA_I*scale,RESID_Z=PARAMS.RESID_Z/(scale if old['threshold_calibration']=='fixed_nominal' else 1))
            kwargs=dict(p=p,degrade=old['attack']!='none',trace=True,freshness_margin=float(old['clock_margin_s']),rewrite_replay_timestamp=old['family']!='intact_replay')
        new=simulate(old['attack'],'C3',int(old['seed']),**kwargs)
        if filename=='sensitivity_runs.csv':
            trace=new.pop('_trace');onset=p.T_DEG if old['attack']=='spoof' else p.T_ATTACK
            allowed={'replay':{'integrity/replay'},'delay':{'stale-state','stale-update'},'spoof':{'consistency'},'none':set()}[old['attack']]
            correct=[tt for tt,kind in trace['alerts'] if onset<=tt<p.T_ATTACK_END and kind in allowed]
            pre=[(tt,kind) for tt,kind in trace['alerts'] if tt<onset]
            new.update(correct_detection=int(bool(correct)),correct_detection_latency=min(correct)-onset if correct else math.nan,pre_onset_alerts=len(pre),benign_run_alert=int(bool(trace['alerts'])) if old['attack']=='none' else math.nan,pre_onset_hold=int(any(kind in {'stale-state','stale-update','consistency'} for _,kind in pre)))
        for key,value in new.items():
            if key in old and different(value,old[key]):
                changes.append(dict(file=filename,family=old.get('family'),D=old.get('D'),noise_scale=old.get('noise_scale'),calibration=old.get('threshold_calibration'),attack=old['attack'],seed=old['seed'],metric=key,before=old[key],after=value))
report={'checked_C3_runs':counts,'comparison_tolerance':1e-12,'changed_metrics':changes,'other_configurations':'C0-C2 cannot execute the corrected C3 current-consistency branch.'}
(root/'reports/reviewer4_current_loss_fix_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
