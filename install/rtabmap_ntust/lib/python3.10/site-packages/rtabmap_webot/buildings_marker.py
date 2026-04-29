import rclpy
from rclpy.node import Node

from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point


class BuildingMarkerNode(Node):

    def __init__(self):
        super().__init__('building_marker_node')

        self.publisher = self.create_publisher(
            MarkerArray,
            'buildings_marker',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_markers
        )

        # 建築物名稱與座標
        self.buildings = [
            ("Teaching bldg",               7.73,   8.34),  #教學大樓
            ("Management bldg",             16.7,  -1.03),  #營管大樓
            ("Architecture bldg",           22.9,  -1.9),   #建館築
            ("Hengyi bldg",                 -1.39,  7.44),  #恆毅樓
            ("Guard House",                 -4.92,   1.32), #警衛室
            ("Library",                     -6.81,  -0.6),  #圖書館
            ("Juyu bldg",                   -8.48,  -6.03), #聚鈺樓
            ("Gymnasium",                   -9.56,  -10.9), #體育館
            ("Electronics bldg",            -7.96, -16.9),  #電子館
            ("Mechanical Engineering bldg", -0.806, -17.6), #機械樓
            ("Zhongzheng Hall",             3.46,  -5.6),   #中正堂
            ("Integrity bldg",              0.413, -10.4),  #誠信樓
        ]


    def publish_markers(self):

        marker_array = MarkerArray()

        for i, (name, x, y) in enumerate(self.buildings):

            # ===== 參數 =====
            text_height = 0.75
            char_width_factor = 0.6  # 控制框寬

            # ===== 計算框大小 =====
            text_length = len(name)
            box_width = text_length * text_height * char_width_factor
            box_height = text_height * 1.5

            # ===== 文字 Marker =====
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = self.get_clock().now().to_msg()

            text_marker.ns = "buildings_text"
            text_marker.id = i

            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD

            text_marker.pose.position.x = x
            text_marker.pose.position.y = y
            text_marker.pose.position.z = 1.0

            text_marker.pose.orientation.w = 1.0

            text_marker.text = name
            text_marker.scale.z = text_height

            # 文字顏色
            text_marker.color.r = 1.0
            text_marker.color.g = 0.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0

            marker_array.markers.append(text_marker) #註解則關閉文字顯示

            # ===== 外框 Marker =====
            box_marker = Marker()
            box_marker.header.frame_id = "map"
            box_marker.header.stamp = self.get_clock().now().to_msg()

            box_marker.ns = "buildings_box"
            box_marker.id = i + 1000  # 避免ID衝突

            box_marker.type = Marker.LINE_STRIP
            box_marker.action = Marker.ADD

            box_marker.pose.orientation.w = 1.0

            # 框線粗細
            box_marker.scale.x = 0.05

            # 框線顏色
            box_marker.color.r = 0.0
            box_marker.color.g = 1.0
            box_marker.color.b = 0.0
            box_marker.color.a = 1.0

            # ===== 框的四個角 =====
            half_w = box_width / 2
            half_h = box_height / 2
            z = 1.0

            p1 = Point(x=x - half_w, y=y - half_h, z=z)
            p2 = Point(x=x + half_w, y=y - half_h, z=z)
            p3 = Point(x=x + half_w, y=y + half_h, z=z)
            p4 = Point(x=x - half_w, y=y + half_h, z=z)

            box_marker.points = [p1, p2, p3, p4, p1]

            #marker_array.markers.append(box_marker) #註解則關閉文字框線顯示

        self.publisher.publish(marker_array)
        self.get_logger().info("Publishing building markers")


def main(args=None):

    rclpy.init(args=args)

    node = BuildingMarkerNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()