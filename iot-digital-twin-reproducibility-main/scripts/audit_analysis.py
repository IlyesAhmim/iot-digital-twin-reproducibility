#!/usr/bin/env python3
"""Supplementary audit: actual paired statistics and targeted model sensitivity.

Run original run_all.py first, then this file. Results go to the manuscript's
results/ folder by default. No published reference output is overwritten.
All confidence intervals are marginal, not multiplicity-adjusted. The unit of
replication is a seed/run, never a time-grid sample or correlated sliding window.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import itertools
import json
import math
import platform
import shutil
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import cbor2
import numpy as np
from scipy.integrate import quad
from scipy.stats import t, norm

import coap_timeliness as coap
import cose_overhead as cose
from dt_sync_sim import simulate, PARAMS, ATTACKS, CONFIGS

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def numeric_summary(values):
    x = np.array([float(v) for v in values if math.isfinite(float(v))])
    n = len(x)
    if not n:
        return dict(n=0, mean=math.nan, sd=math.nan, ci95_low=math.nan,
                    ci95_high=math.nan, median=math.nan, p95=math.nan)
    mean = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else math.nan
    half = float(t.ppf(.975, n - 1) * sd / np.sqrt(n)) if n > 1 else math.nan
    return dict(n=n, mean=mean, sd=sd, ci95_low=mean-half,
                ci95_high=mean+half, median=float(np.median(x)),
                p95=float(np.quantile(x, .95)))


def wilson(k, n):
    z = norm.ppf(.975)
    ph = k / n
    den = 1 + z*z/n
    center = (ph + z*z/(2*n)) / den
    half = z * np.sqrt(ph*(1-ph)/n + z*z/(4*n*n)) / den
    return float(max(0, center-half)), float(min(1, center+half))


def original_statistics(out):
    source = ROOT / 'results/reproduced/sim_results.csv'
    shutil.copyfile(source, out / 'simulation_runs.csv')
    with source.open() as f:
        rows = list(csv.DictReader(f))
    groups = defaultdict(list)
    for r in rows:
        groups[(r['attack'],r['config'])].append(r)
    metrics = ['I1_meas_mean','age_true_mean','I2_meas','I2_true',
               'I3_apparent','I3_true','I4','I5','I7_rmse','I10','action_minus_tstar']
    stats = []
    for (attack, config), rs in groups.items():
        for metric in metrics:
            stats.append(dict(attack=attack,config=config,metric=metric,
                              method='Student_t_mean_95',**numeric_summary(r[metric] for r in rs)))
        k = sum(bool(r['first_alert_kind']) for r in rs)
        lo, hi = wilson(k,len(rs))
        stats.append(dict(attack=attack,config=config,metric='runs_with_alert',
                          method='Wilson_binomial_95',n=len(rs),mean=k/len(rs),
                          ci95_low=lo,ci95_high=hi,successes=k))
    write_csv(out/'statistical_summary.csv',stats)
    paired = []
    for attack in ATTACKS:
        for c_a,c_b in [('C1','C0'),('C2','C1'),('C3','C2')]:
            aa={r['seed']:r for r in groups[(attack,c_a)]}
            bb={r['seed']:r for r in groups[(attack,c_b)]}
            assert aa.keys()==bb.keys()
            for metric in ['I1_meas_mean','age_true_mean','I7_rmse','I10','action_minus_tstar']:
                diffs=[float(aa[s][metric])-float(bb[s][metric]) for s in aa]
                paired.append(dict(attack=attack,contrast=f'{c_a}-{c_b}',metric=metric,
                                   method='paired_Student_t_mean_difference_95',**numeric_summary(diffs)))
    write_csv(out/'paired_comparisons.csv',paired)
    return rows


def sensitivity(out):
    runs=[]
    # One factor at a time: bounds compared using exactly the same random streams.
    cases=[('freshness_bound',d,1.0,'calibrated',0.0) for d in [.5,1.,2.,5.]]
    cases += [('noise_scale',2.,s,'calibrated',0.) for s in [.5,2.]]
    cases += [('noise_scale',2.,2.,'fixed_nominal',0.)]
    cases += [('clock_guard',2.,1.,'calibrated',PARAMS.CLOCK_ERR)]
    cases += [('intact_replay',2.,1.,'calibrated',0.)]
    for family,d,scale,calibration,margin in cases:
        configs=['C2','C3'] if family in ('freshness_bound','clock_guard') else ['C3']
        attacks=ATTACKS if family in ('freshness_bound','clock_guard') else ['none','spoof']
        if family=='intact_replay':
            configs=['C1','C2','C3'];attacks=['replay']
        p=replace(PARAMS,D=d,SIGMA_V=PARAMS.SIGMA_V*scale,
                  SIGMA_I=PARAMS.SIGMA_I*scale,
                  RESID_Z=PARAMS.RESID_Z/(scale if calibration=='fixed_nominal' else 1))
        for attack in attacks:
            for config in configs:
                for seed_index in range(1,31):
                    seed=1000*ATTACKS.index(attack)+seed_index
                    r=simulate(attack,config,seed,p=p,degrade=attack!='none',trace=True,
                               freshness_margin=margin,
                               rewrite_replay_timestamp=family!='intact_replay')
                    trace=r.pop('_trace')
                    onset=p.T_DEG if attack=='spoof' else p.T_ATTACK
                    allowed={'replay':{'integrity/replay'},'delay':{'stale-state','stale-update'},
                             'spoof':{'consistency'},'none':set()}[attack]
                    correct=[tt for tt,kind in trace['alerts'] if onset<=tt<p.T_ATTACK_END and kind in allowed]
                    pre=[(tt,kind) for tt,kind in trace['alerts'] if tt<onset]
                    r.update(family=family,D=d,noise_scale=scale,threshold_calibration=calibration,
                             clock_margin_s=margin,degradation=attack!='none',
                             correct_detection=int(bool(correct)),
                             correct_detection_latency=min(correct)-onset if correct else math.nan,
                             pre_onset_alerts=len(pre),
                             benign_run_alert=int(bool(trace['alerts'])) if attack=='none' else math.nan,
                             pre_onset_hold=int(any(kind in {'stale-state','stale-update','consistency'} for _,kind in pre)))
                    runs.append(r)
        print(f'sensitivity: {family} D={d} noise={scale} calibration={calibration} margin={margin}',flush=True)
    write_csv(out/'sensitivity_runs.csv',runs)
    grouped=defaultdict(list)
    fields=['family','D','noise_scale','threshold_calibration','clock_margin_s','attack','config']
    for r in runs:
        grouped[tuple(r[k] for k in fields)].append(r)
    summ=[]
    for key,rs in grouped.items():
        row=dict(zip(fields,key))
        row['n_runs']=len(rs)
        for name in ['correct_detection','benign_run_alert','pre_onset_hold']:
            vals=[r[name] for r in rs if math.isfinite(r[name])]
            if vals:
                row[name+'_count']=int(sum(vals));row[name+'_rate']=sum(vals)/len(vals)
                row[name+'_ci95_low'],row[name+'_ci95_high']=wilson(sum(vals),len(vals))
        for metric in ['correct_detection_latency','I1_meas_mean','age_true_mean',
                       'I7_rmse','I10','action_minus_tstar','n_alerts']:
            for k,v in numeric_summary(r[metric] for r in rs).items():
                row[metric+'_'+k]=v
        summ.append(row)
    write_csv(out/'sensitivity_analysis.csv',summ)
    return len(runs)


def coap_independent(out):
    # Enumeration over all 32 loss patterns, with separate quadrature over T0.
    rows=[]
    for p in [0.,.05,.1,.2,.3,.4,.5,1.]:
        for d in [.05,.5,2.5]:
            for deadline in [.5,1.,2.,5.,10.,20.,50.]:
                total=0.;deliv=0.
                for pattern in itertools.product([False,True],repeat=5): # True = loss
                    mass=p**sum(pattern)*(1-p)**(5-sum(pattern))
                    first=next((i for i,lost in enumerate(pattern) if not lost),None)
                    if first is None: continue
                    deliv+=mass
                    factor=2**first-1
                    cuts=[(deadline-d)/factor] if factor and 2<(deadline-d)/factor<3 else None
                    prob=quad(lambda t0: float(factor*t0+d<=deadline),2.,3.,points=cuts)[0]
                    total+=mass*prob
                analytical=coap.p_timely(p,deadline,d)
                assert abs(total-analytical)<1e-12
                assert abs(deliv-coap.p_delivered(p))<1e-12
                rows.append(dict(loss_probability=p,one_way_delay_s=d,deadline_s=deadline,
                                 enumeration_timely=total,closed_form_timely=analytical,
                                 eventual_delivery=deliv,absolute_difference=abs(total-analytical)))
    write_csv(out/'coap_independent_checks.csv',rows)
    mc=[]
    for p in [.05,.1,.2,.3,.4,.5]:
        for deadline in [2.,5.,10.,20.]:
            md,mt=coap.monte_carlo(p,deadline)
            mc.append(dict(p=p,deadline_s=deadline,n=400000,seed=1,
                           mc_delivery=md,closed_delivery=coap.p_delivered(p),
                           mc_timely=mt,closed_timely=coap.p_timely(p,deadline),
                           max_absolute_error=max(abs(md-coap.p_delivered(p)),abs(mt-coap.p_timely(p,deadline)))))
    write_csv(out/'coap_monte_carlo.csv',mc)
    # Illustrative attempt-indexed two-state loss process, stationary P(loss)=p.
    # beta=P(loss at next attempt | previous loss); not a physical-time channel.
    burst=[]
    rng=np.random.default_rng(20261104)
    n=400000;p=.2
    for beta in [.2,.5,.8]:
        alpha=p*(1-beta)/(1-p)
        lost=np.empty((n,5),dtype=bool)
        lost[:,0]=rng.random(n)<p
        for i in range(1,5):
            lost[:,i]=rng.random(n)<np.where(lost[:,i-1],beta,alpha)
        t0=rng.uniform(2,3,n)
        delivered=(~lost).any(axis=1)
        first=(~lost).argmax(axis=1)
        ages=(2.**first-1)*t0+.05
        for deadline in [2.,5.,10.,20.]:
            masses=[1-p]+[p*beta**(i-1)*(1-beta) for i in range(1,5)]
            prob=sum(m*coap.p_send_by(i,deadline-.05) for i,m in enumerate(masses))
            burst.append(dict(stationary_loss=p,loss_given_loss=beta,loss_given_success=alpha,
                              deadline_s=deadline,eventual_delivery=1-p*beta**4,
                              timely=prob,mc_delivery=float(delivered.mean()),
                              mc_timely=float((delivered&(ages<=deadline)).mean()),
                              trials=n,seed=20261104))
    write_csv(out/'coap_correlated_loss_sensitivity.csv',burst)
    return max(r['max_absolute_error'] for r in mc)


def sizes_and_clock(out):
    pl=cose.float32_payload()
    rows=[]
    for name,alg,n_sig in [('Ed25519',-8,64),('ES256',-7,64),
                           ('ML-DSA-44',-48,2420),('ML-DSA-65',-49,3309),('ML-DSA-87',-50,4627)]:
        # Fixed-length placeholders only: this verifies serialized size, not PQ signing.
        message,_,_=cose.cose_sign1(pl,alg,lambda data: bytes(n_sig))
        obj=cbor2.loads(message)
        assert obj.tag==18 and len(obj.value[3])==n_sig
        rows.append(dict(algorithm=name,COSE_algorithm=alg,payload_bytes=len(pl),
                         signature_bytes=n_sig,object_bytes=len(message),
                         overhead_bytes=len(message)-len(pl),method='CBOR_encoding_fixed_length_placeholder_signature'))
    assert [r['object_bytes'] for r in rows]==[100,100,2458,3347,4665]
    write_csv(out/'cose_extended_sizes.csv',rows)
    rng=np.random.default_rng(20261104)
    n=1000000
    age=rng.uniform(0,5,n); e_s=rng.uniform(-.005,.005,n); e_t=rng.uniform(-.005,.005,n)
    estimated=age+e_t-e_s
    epsilon=.010
    assert np.all(age<=estimated+epsilon+1e-14)
    accepted=estimated+epsilon<=2
    assert np.all(age[accepted]<=2)
    report=dict(samples=n,seed=20261104,per_clock_error_s=.005,
                conservative_difference_bound_s=epsilon,accepted=int(accepted.sum()),
                false_fresh_acceptances=int(np.sum(accepted&(age>2))),
                interpretation='Numerical sanity check; the algebraic proof, not sampling, establishes the guarantee.')
    (out/'clock_bound_check.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'results')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    rows=original_statistics(out)
    count=sensitivity(out)
    worst=coap_independent(out)
    sizes_and_clock(out)
    metadata=dict(audit_date='2026-11-05',python=platform.python_version(),
                  packages={name:importlib.metadata.version(name) for name in
                            ['numpy','scipy','matplotlib','cbor2','cryptography']},
                  original_runs=len(rows),sensitivity_runs=count,
                  coap_max_mc_absolute_error=worst,
                  inference_unit='independent seed within scenario; configurations paired by seed',
                  original_source_sha256=hashlib.sha256((ROOT/'results/reproduced/sim_results.csv').read_bytes()).hexdigest())
    (out/'audit_environment.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    main()
