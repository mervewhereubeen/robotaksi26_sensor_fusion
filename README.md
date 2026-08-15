# Robotaksi26 Sensor Fusion

ROS 2 tabanlı, **ZED odometri + Xsens IMU** kullanan sensor fusio modeli.

Filtre olarak `robot_localization` paketinin **UKF (Unscented Kalman Filter)** düğümü kullanılmaktadır.

## Final Sensor Assignment

- **ZED Odometry** → X, Y, Z position
- **Xsens IMU** → Roll, Pitch, Yaw orientation
- **UKF Output** → `/ukf/odometry`

Final UKF çıkış frekansı:

```text
~30 Hz
```

---

# Architecture

```text
/zed/zed_node/odom
        |
        v
zed_cov_injector
        |
        v
/zed/zed_node/odom_with_covariance
        |
        | X, Y, Z
        v
      +-----+
      | UKF | -----------------> /ukf/odometry
      +-----+
        ^
        | Roll, Pitch, Yaw
        |
/imu/with_covariance
        ^
        |
imu_cov_injector
        ^
        |
    /imu/data
```

UKF state order:

```text
[X, Y, Z,
 Roll, Pitch, Yaw,
 vX, vY, vZ,
 vRoll, vPitch, vYaw,
 aX, aY, aZ]
```

Current fusion configuration:

```text
ZED -> X, Y, Z

IMU -> Roll, Pitch, Yaw

Velocity states -> UKF tarafından dahili olarak tahmin edilir

Linear acceleration -> fuse edilmiyor
```

---

# Important ZED Covariance Fix

Testler sırasında ham ZED odometrisinin pose covariance değerlerinin yaklaşık:

```text
1e-10
```

seviyesinde yayınlandığı gözlemlendi.

Bu değer UKF için gerçekçi olmayacak kadar küçük olduğundan filtre ZED pozisyon ölçümlerine aşırı güveniyor ve ölçülmeyen `vX` / `vY` state'lerinde kararsızlık oluşuyordu.

Eski davranışta:

```text
Max XY jump       ≈ 4.6 m
Max UKF XY speed  ≈ 46 m/s
```

gibi fiziksel olarak mümkün olmayan sonuçlar görülüyordu.

Bu problemi çözmek için:

```text
zed_cov_injector.py
```

eklendi.

Akış:

```text
/zed/zed_node/odom
        |
        v
zed_cov_injector
        |
        v
/zed/zed_node/odom_with_covariance
        |
        v
       UKF
```

UKF artık doğrudan:

```text
/zed/zed_node/odom
```

yerine:

```text
/zed/zed_node/odom_with_covariance
```

topic'ini kullanmaktadır.

`zed_cov_injector` kaldırılmamalı veya bypass edilmemelidir; ZED covariance problemi upstream tarafta düzeltilirse yeniden değerlendirilebilir.

---

# Repository Structure

```text
robot_fusion/
├── config/
│   ├── ukf_config.yaml
│   └── ukf_config_FINAL_frozen_2026-08-14.yaml
│
├── launch/
│   └── fusion.launch.py
│
├── robot_fusion/
│   ├── __init__.py
│   ├── imu_cov_injector.py
│   └── zed_cov_injector.py
│
├── resource/
│   └── robot_fusion
│
├── package.xml
├── setup.cfg
└── setup.py
```

Aktif config:

```text
config/ukf_config.yaml
```

Final doğrulanmış ve dondurulmuş config:

```text
config/ukf_config_FINAL_frozen_2026-08-14.yaml
```

---

# Requirements

Test edilen sistem:

```text
Ubuntu
ROS 2 Humble
robot_localization
Python 3
```

ROS 2 Humble ortamı:

```bash
source /opt/ros/humble/setup.bash
```

`robot_localization` sistemde bulunmalıdır.

Gerekirse:

```bash
sudo apt install ros-humble-robot-localization
```

---

# Clone

Yeni bir ROS 2 workspace oluşturun:

```bash
mkdir -p ~/sensor_fusion_ws/src
cd ~/sensor_fusion_ws/src
```

Repository'yi clone edin:

```bash
git clone https://github.com/mervewhereubeen/robotaksi26_sensor_fusion.git robot_fusion
```

Workspace:

```text
~/sensor_fusion_ws/
└── src/
    └── robot_fusion/
```

şeklinde olmalıdır.

---

# Build

```bash
cd ~/sensor_fusion_ws

source /opt/ros/humble/setup.bash

colcon build --symlink-install
```

Başarılı build sonunda yaklaşık:

```text
Summary: 1 package finished
```

görülmelidir.

Daha sonra:

```bash
source ~/sensor_fusion_ws/install/setup.bash
```

---

# Required Input Topics

Gerçek araç üzerinde fusion başlatılmadan önce sensör driver'ları çalışıyor olmalıdır.

Gerekli ana input topic'leri:

```text
/imu/data
/zed/zed_node/odom
```

Kontrol:

```bash
ros2 topic list
```

IMU geliyor mu:

```bash
ros2 topic hz /imu/data
```

ZED odometri geliyor mu:

```bash
ros2 topic hz /zed/zed_node/odom
```

Tek mesaj kontrolü:

```bash
ros2 topic echo /imu/data --once
```

```bash
ros2 topic echo /zed/zed_node/odom --once
```

Bu iki topic gelmeden UKF'nin düzgün çalışması beklenmemelidir.

---

# Run on Real Vehicle

Önce ROS ortamını source edin:

```bash
source /opt/ros/humble/setup.bash
source ~/sensor_fusion_ws/install/setup.bash
```

Fusion paketini başlatın:

```bash
ros2 launch robot_fusion fusion.launch.py
```

## Important

Gerçek araç üzerinde:

```text
use_sim_time = false
```

olmalıdır.

Bag playback testlerinde kullanılan:

```bash
ros2 param set /ukf_filter_node use_sim_time true
```

gibi komutlar **gerçek araç üzerinde kullanılmamalıdır**.

Gerçek sensör timestamp'leri kullanılmalıdır.

---

# Output

Final fusion output topic:

```text
/ukf/odometry
```

Frekans kontrolü:

```bash
ros2 topic hz /ukf/odometry
```

Steady-state beklenen değer:

```text
~30 Hz
```

Tek bir UKF mesajını görmek için:

```bash
ros2 topic echo /ukf/odometry --once
```

---

# Diagnostics

UKF diagnostics kontrolü:

```bash
ros2 topic echo /diagnostics --once
```

Başlangıç transient'i bittikten sonra beklenen mesaj:

```text
The robot_localization state estimation node appears to be functioning properly.
```

Beklenen UKF frekansı:

```text
Actual frequency ≈ 30 Hz
```

İlk yaklaşık 5 saniyede diagnostic frequency kontrolünden kaynaklanan startup WARN/ERROR mesajları görülebilir.

Testlerde bu uyarılar startup sonrasında kaybolmuş ve steady-state sırasında tekrar etmemiştir.

---

# RViz Visualization

RViz başlatın:

```bash
rviz2
```

## Global Options

```text
Fixed Frame = odom
```

## Add Odometry - UKF

```text
Topic = /ukf/odometry
```

## Add Odometry - ZED

```text
Topic = /zed/zed_node/odom_with_covariance
```

İki Odometry display'ine farklı renk verilmesi önerilir.

Örneğin:

```text
UKF = red
ZED = blue
```

`Keep` değeri:

```text
100 - 200
```

olarak ayarlanabilir.

---

# What Should Be Seen in RViz?

Sağlıklı sistemde:

- ZED trajectory düzgün ve sürekli olmalıdır.
- UKF trajectory düzgün ve sürekli olmalıdır.
- UKF ve ZED XY trajectory'leri birbirine yakın ilerlemelidir.
- UKF bir anda birkaç metre başka konuma sıçramamalıdır.
- UKF zamanla ZED'den belirgin şekilde kopmamalıdır.
- Büyük teleport veya divergence görülmemelidir.

Final testlerde ZED ve UKF trajectory'leri RViz üzerinde birbirini yakından takip etmiştir.

## Important Orientation Note

Final configuration:

```text
ZED -> X, Y, Z
IMU -> Roll, Pitch, Yaw
```

olduğu için ZED Odometry arrow orientation ile UKF arrow orientation birebir aynı olmak zorunda değildir.

ZED ve IMU heading referansları aynı değildir.

Bu nedenle ilk görsel kontrol:

```text
XY trajectory alignment
```

üzerinden yapılmalıdır.

---

# TF Visualization

RViz içerisinde:

```text
Add -> TF
```

eklenebilir.

Beklenen TF tree:

```text
odom
└── base_link
    ├── imu_link
    ├── zed_camera_link
    └── velodyne
```

TF display için önerilen ayarlar:

```text
Show Names  = enabled
Show Axes   = enabled
Show Arrows = enabled
```

Araç hareket ederken:

```text
base_link
imu_link
zed_camera_link
```

birbirlerine göre sabit kalmalıdır.

Sensör frame'leri `base_link` üzerinden kopmamalı veya başka konuma sıçramamalıdır.

---

# Current TF Configuration

## IMU

```text
base_link -> imu_link

x = +1.44 m
y =  0.00 m
z = +1.39 m

rotation = identity
```

## ZED

```text
base_link -> zed_camera_link

x = -0.205 m
y =  0.000 m
z = +0.685 m

rotation = identity
```

## Important

Bu transformlar yazılım tarafında doğrulanmıştır.

Ancak gerçek araç üzerinde sensörlerin fiziksel montaj konumları ölçülerek bu değerlerin doğruluğu ayrıca kontrol edilmelidir.

Yanlış sensör lever-arm değerleri gerçek araç performansını etkileyebilir.

---

# Recommended First Real-Vehicle Test

İlk saha testinde agresif sürüş yapılmaması önerilir.

Sırasıyla:

1. Araç sabit
2. Çok yavaş düz sürüş
3. Dur-kalk
4. Hafif dönüş
5. Daha uzun düz sürüş
6. Normal dönüşler

Her aşamada aşağıdaki topic'ler kontrol edilmelidir:

```text
/ukf/odometry
/diagnostics
/zed/zed_node/odom_with_covariance
```

Kontrol edilmesi gerekenler:

- X/Y position'da ani metre seviyesinde jump var mı?
- UKF velocity fiziksel olarak mantıklı mı?
- NaN / Inf var mı?
- Diagnostics steady-state'te temiz mi?
- UKF yaklaşık 30 Hz çalışıyor mu?
- RViz üzerinde ZED ve UKF trajectory birbirine yakın mı?

---

# ROS Bag Recording for Debugging

Gerçek araç testinde problem görülürse mutlaka bag kaydı alınmalıdır.

Önerilen kayıt:

```bash
ros2 bag record \
/imu/data \
/zed/zed_node/odom \
/zed/zed_node/odom_with_covariance \
/ukf/odometry \
/diagnostics \
/tf \
/tf_static
```

Bu kayıt ile problem daha sonra offline olarak tekrar analiz edilebilir.

---

# Final Validation Results

Final sistem aynı dataset ve aynı sürüş segmenti üzerinde tekrar tekrar test edilmiştir.

Covariance fix öncesinde:

```text
Max XY jump       ≈ 3.8 - 4.6 m
Max UKF XY speed  ≈ 44 - 46 m/s
```

gibi fiziksel olarak mümkün olmayan UKF state'leri görülüyordu.

Covariance fix sonrasında:

```text
Max XY step       ≈ 0.13 m
Max UKF XY speed  ≈ 1.13 - 1.14 m/s
NaN / Inf         = 0
UKF steady-state  ≈ 30 Hz
```

elde edilmiştir.

RViz görsel testinde:

```text
ZED trajectory   -> smooth
UKF trajectory   -> smooth
XY alignment     -> close
large teleport   -> none
TF tree          -> connected
```

sonuçları gözlemlenmiştir.

---

# Final Configuration

Final state assignment:

```text
ZED:
X
Y
Z

IMU:
Roll
Pitch
Yaw
```

Final UKF output:

```text
/ukf/odometry
```

Final filter:

```text
robot_localization / ukf_node
```

Frequency:

```text
30 Hz
```

---

# Status

```text
Final 2-Sensor Version

ZED + Xsens IMU
ROS 2 Humble
robot_localization UKF

Validated:
- Numerical validation: PASS
- Diagnostics: PASS
- RViz visual validation: PASS
- TF runtime validation: PASS
- Clean build: PASS
- Clean launch: PASS
```
