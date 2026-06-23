from setuptools import setup, find_packages

package_name = "turtlebot_delivery"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[("share/ament_index/resource_index/packages", ["resource/" + package_name]), ("share/" + package_name, ["package.xml"])],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="yjmini",
    maintainer_email="u79jm@koreatech.ac.kr",
    description="Mock-first package for smart assembly transport MVP.",
    license="MIT",
    entry_points={"console_scripts": ["turtlebot-delivery-round-trip=turtlebot_delivery.delivery_round_trip:main"]},
)
