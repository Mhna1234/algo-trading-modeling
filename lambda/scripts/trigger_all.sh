#!/bin/bash
# Trigger all 3 Lambda partitions asynchronously

AWS_REGION="eu-north-1"

echo "Triggering Benchmark Lambdas..."

for p in 1 2 3; do
    func="benchmark-calculator-partition-$p"
    echo "Invoking $func..."
    aws.exe lambda invoke --function-name $func --region $AWS_REGION --invocation-type Event response_$p.json
    echo "  Triggered (Async)"
done

echo "All triggered. Check S3 in ~15 minutes."
