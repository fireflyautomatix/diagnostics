import os

import unittest

from launch import LaunchDescription
from launch.actions import ExecuteProcess

import launch_testing
import launch_testing.actions
import launch_testing.asserts
import launch_testing.util

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus

import rclpy
from rclpy.node import Node


def generate_test_description():
    aggregator_node = ExecuteProcess(
        cmd=[
            os.environ["AGGREGATOR_NODE"],
            "--ros-args",
            "--params-file",
            os.environ["PARAMETER_FILE"],
        ],
        name="aggregator_node",
        emulate_tty=True,
        output="screen",
    )

    launch_description = LaunchDescription()
    launch_description.add_action(aggregator_node)
    launch_description.add_action(launch_testing.util.KeepAliveProc())
    launch_description.add_action(launch_testing.actions.ReadyToTest())
    return launch_description, locals()


class TestNode(Node):
    def __init__(self):
        super().__init__("test_node")
        stateful_qos = rclpy.qos.QoSProfile(
            history=rclpy.qos.QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            durability=rclpy.qos.QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.stateful_sub = self.create_subscription(
            DiagnosticArray,
            "diagnostics_agg_stateful",
            self.stateful_agg_callback,
            stateful_qos,
        )
        self.last_received_stateful_msg = None
        self.stateful_pub = self.create_publisher(
            DiagnosticArray, "diagnostics_stateful", stateful_qos
        )

    def stateful_agg_callback(self, msg):
        self.last_received_stateful_msg = msg


class TestStatefulAggregation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(self):
        rclpy.shutdown()

    def setUp(self):
        self.test_node = TestNode()

    def tearDown(self):
        self.test_node.destroy_node()

    def test_is_stateful_publisher(self, launch_service, proc_info, proc_output):
        timeout_seconds = 1.1  # avoiding round number of 1.0
        messages = []

        rclpy.spin_once(self.test_node, timeout_sec=timeout_seconds)
        messages.append(self.test_node.last_received_stateful_msg)
        self.assertIsNotNone(messages[-1])

        rclpy.spin_once(self.test_node, timeout_sec=timeout_seconds)
        messages.append(self.test_node.last_received_stateful_msg)
        # if the publisher were not stateful, the messages would not be equal,
        # they would have different headers
        self.assertEqual(messages[-2], messages[-1])

        self.test_node.stateful_pub.publish(
            DiagnosticArray(
                status=[DiagnosticStatus(name="primary", level=DiagnosticStatus.OK)]
            )
        )

        rclpy.spin_once(self.test_node, timeout_sec=timeout_seconds)
        messages.append(self.test_node.last_received_stateful_msg)
        self.assertIsNotNone(messages[-1])
        self.assertEqual(messages[-1].status[0].level, DiagnosticStatus.OK)

        rclpy.spin_once(self.test_node, timeout_sec=timeout_seconds)
        messages.append(self.test_node.last_received_stateful_msg)
        self.assertEqual(messages[-2], messages[-1])

        self.test_node.stateful_pub.publish(
            DiagnosticArray(
                status=[DiagnosticStatus(name="primary", level=DiagnosticStatus.OK)]
            )
        )

        # even though we published a message, the aggregator should not have
        # published *out* a  message since the overall aggregation is still
        # the same
        rclpy.spin_once(self.test_node, timeout_sec=timeout_seconds)
        messages.append(self.test_node.last_received_stateful_msg)
        self.assertEqual(messages[-2], messages[-1])


@launch_testing.post_shutdown_test()
class TestAggregatorShutdown(unittest.TestCase):
    def test_last_process_exit_code(self, proc_info, aggregator_node):
        launch_testing.asserts.assertExitCodes(proc_info, process=aggregator_node)
