#!/bin/zsh
cd /Users/devansh/vishwas
source .venv/bin/activate

ALL_BUT_SPREAD="lead_day,gh500_mean,gh500_spread,u500_mean,u500_spread,v500_mean,v500_spread,pwat_mean,pwat_spread,cape_mean,cape_spread,precip_mean,gh500_gradient,wind500_speed,u850_mean,v850_mean,shear_500_850,flow500_deformation,month,pwat_anomaly,cape_anomaly,precip_anomaly"

run () {   # name, drop-list
  echo "=== $1 ==="
  if [ -z "$2" ]; then
    python src/07_model.py --bootstrap 500 --seed 0 \
      --out data/pred_$1.parquet > ablations/$1.log 2>&1
  else
    python src/07_model.py --bootstrap 500 --seed 0 --drop "$2" \
      --out data/pred_$1.parquet > ablations/$1.log 2>&1
  fi
  echo "    exit=$? $(date +%H:%M:%S)"
}

run a_full        ""
run b_no_month    "month"
run c_no_precip   "precip_mean,precip_spread"
run d_no_850      "shear_500_850,u850_mean,v850_mean"
run e_spread_only "$ALL_BUT_SPREAD"
echo "ALL ABLATIONS DONE"
