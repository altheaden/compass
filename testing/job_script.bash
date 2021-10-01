#!/bin/bash -l
#SBATCH --nodes=2
#SBATCH --time=2:00:00
#SBATCH --job-name=cosine_bell
#SBATCH --output=cosine_bell.o%j
#SBATCH --error=cosine_bell.e%j

# todo: generalize load script
source ./load_compass_env.sh

for mesh in QU60 QU90 QU120 QU150 QU180 QU210 QU240
do
  ./run_res.py -m $mesh &
done

wait

cd analysis
compass run
cd ..

# to do: how do we srun a job that waits for another job
