# Aggregator Example

This is a simple example to show the diagnostic_aggregator in action. It involves one python script producing dummy diagnostic data ([example_pub.py](./example_pub.py)), and one diagnostic aggregator configuration ([example.yaml](./example.yaml)) that provides analyzers aggregating it.

Run the example with `ros2 launch diagnostic_aggregator example.launch.py`

## Stateful
To run the aggregator with stateful publishers and transient_local qos, run the example with `ros2 launch diagnostic_aggregator example.launch.py publish_statefully:=True`