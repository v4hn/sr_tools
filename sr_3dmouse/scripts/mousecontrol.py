#!/usr/bin/env python

import rospy
import tf
from sr_robot_commander.sr_arm_commander import SrArmCommander
from sr_robot_commander.sr_robot_commander import SrRobotCommander
from geometry_msgs.msg import PoseStamped
from geometry_msgs.msg import Pose
from sensor_msgs.msg import Joy
from copy import deepcopy


class MouseCommand():

    def __init__(self):
        # map 3d mouse buttons
        self.buttons = {"linearX": 0,
                        "linearY": 1,
                        "linearZ": 2,
                        "angularX": 3,
                        "angularY": 4,
                        "angularZ": 5}

        self.data = Joy()
        self.start_pose = Pose()
        #subscribe to mouse topic
        self.sub = rospy.Subscriber("/spacenav/joy", Joy, self.joy_msg_callback)
        self._arm_commander = SrArmCommander(name="right_arm", set_ground=True)
        #self._arm_commander = SrRobotCommander(name="right_arm")
        self.names = self._arm_commander._move_group_commander._g.get_active_joints()
        print "Active joints: " + str(self.names)
        self.pub = rospy.Publisher("command", PoseStamped, queue_size=1)

    def joy_msg_callback(self, data):
        # retrieve the mouse 3d data
        self.data = data

    def update_robot_pose(self):

        rate = rospy.Rate(100)
        while not rospy.is_shutdown():
            self.start_pose = deepcopy(self._arm_commander.get_current_pose())
            self.compute_joy_pose(self.start_pose)
            rate.sleep()

    def compute_joy_pose(self, start_pose):
        # might need adjustment on real robot
        scale = 5
        roll = 0.0
        pitch = 0.0
        yaw = 0.0

        # set new position for the robot
        new_pose = PoseStamped()
        new_pose.header.stamp = rospy.get_rostime()
        new_pose.header.frame_id = "world"
        new_pose.pose = deepcopy(start_pose)

        # retrieve joy commands
        new_pose.pose.position.x += (self.data.axes[self.buttons['linearX']])/scale
        new_pose.pose.position.y += (self.data.axes[self.buttons['linearY']])/scale
        new_pose.pose.position.z += (self.data.axes[self.buttons['linearZ']])/scale

        # set new rotation for joint handle from joystick
        yaw += (self.data.axes[self.buttons['angularZ']])/scale
        roll += (self.data.axes[self.buttons['angularX']])/scale
        pitch += (self.data.axes[self.buttons['angularY']])/scale


        # create quaternion to add to current rotation. Reverse pitch and yaw
        diff_quaternion = tf.transformations.quaternion_from_euler(roll, pitch*-1, yaw*-1)

        start_pose_quaternion = (
                 start_pose.orientation.x,
                 start_pose.orientation.y,
                 start_pose.orientation.z,
                 start_pose.orientation.w)

        # multiply current quaternion and difference
        new_pose_quaternion = tf.transformations.quaternion_multiply(start_pose_quaternion, diff_quaternion)

        new_pose.pose.orientation.x = new_pose_quaternion[0]
        new_pose.pose.orientation.y = new_pose_quaternion[1]
        new_pose.pose.orientation.z = new_pose_quaternion[2]
        new_pose.pose.orientation.w = new_pose_quaternion[3]
        # move arm
        #self._arm_commander.move_to_pose_target(new_pose.pose)
        self._arm_commander.move_to_pose_value_target_unsafe(new_pose, avoid_collisions=True, time=0.3, wait=False)
        self.pub.publish(new_pose)

if __name__ == '__main__':
    rospy.init_node("mouse_tele_op", anonymous=True)
    MouseSim = MouseCommand()
    #update pose
    MouseSim.update_robot_pose()
    rospy.spin()