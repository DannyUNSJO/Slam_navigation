import cv2
import yaml
import numpy as np
from skimage.metrics import structural_similarity as ssim

# =========================
# 絕對路徑
# =========================
BASE_PATH = "/home/danny/ros2_ws/src/rtabmap_webot/Evaluate"

GT_PGM = BASE_PATH + "/gt.pgm"
GT_YAML = BASE_PATH + "/gt.yaml"

SLAM_PGM = BASE_PATH + "/nav2_map.pgm"
SLAM_YAML = BASE_PATH + "/nav2_map.yaml"


# =========================
# 讀 map
# =========================
def load_map(pgm_path, yaml_path):
    img = cv2.imread(pgm_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise FileNotFoundError(f"Cannot load: {pgm_path}")

    with open(yaml_path, 'r') as f:
        meta = yaml.safe_load(f)

    return img, meta


# =========================
# binary map（IoU）
# =========================
def to_binary(img):
    return (img < 100).astype(np.uint8)


# =========================
# align origin (調整原點對齊)
# =========================
def align_origin(gt_origin, slam_origin):
    # 計算平移偏移量
    offset_x = gt_origin[0] - slam_origin[0]
    offset_y = gt_origin[1] - slam_origin[1]
    
    return offset_x, offset_y


# =========================
# Phase Correlation（用於精確對齊）
# =========================
def align_using_phase_correlation(img1, img2):
    # 確保兩張圖的大小一致
    img1_resized = cv2.resize(img1, (img2.shape[1], img2.shape[0]))
    
    # Convert both images to float32 for phase correlation
    img1_float = np.float32(img1_resized)
    img2_float = np.float32(img2)
    
    # Phase correlation
    shift, response = cv2.phaseCorrelate(img1_float, img2_float)
    
    # Extract shift values (dx, dy)
    dx, dy = shift
    print(f"Phase correlation shift: dx={dx}, dy={dy}, response={response}")

    # Apply translation (alignment)
    translation_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    aligned_img = cv2.warpAffine(img1_resized, translation_matrix, (img2.shape[1], img2.shape[0]))

    return aligned_img


# =========================
# IoU
# =========================
def compute_iou(a, b):
    intersection = np.logical_and(a, b)
    union = np.logical_or(a, b)

    if np.sum(union) == 0:
        return 0.0

    return np.sum(intersection) / np.sum(union)


# =========================
# main
# =========================
if __name__ == "__main__":

    print("Loading maps...")

    gt_img, gt_meta = load_map(GT_PGM, GT_YAML)
    slam_img, slam_meta = load_map(SLAM_PGM, SLAM_YAML)

    print("GT shape:", gt_img.shape)
    print("SLAM shape:", slam_img.shape)

    # =========================
    # align origin（對齊原點）
    # =========================
    gt_origin = gt_meta['origin']  # [-20.0, -20.0]
    slam_origin = slam_meta['origin']  # [-10.7, -21.5]
    
    offset_x, offset_y = align_origin(gt_origin, slam_origin)

    # =========================
    # 使用 Phase Correlation 對齊地圖
    # =========================
    slam_aligned = align_using_phase_correlation(slam_img, gt_img)

    # =========================
    # 轉換為 binary（IoU 計算）
    # =========================
    gt_bin = to_binary(gt_img)
    slam_bin = to_binary(slam_aligned)

    # =========================
    # mask（Nav2 unknown=205）
    # =========================
    mask = (slam_img != 205).astype(np.uint8)

    # =========================
    # ⭐ 強制調整 mask 和 SLAM 地圖的尺寸一致
    # =========================
    mask = cv2.resize(mask, (gt_bin.shape[1], gt_bin.shape[0]))  # resize mask
    slam_bin = cv2.resize(slam_bin, (gt_bin.shape[1], gt_bin.shape[0]))  # resize SLAM map
    slam_aligned = cv2.resize(slam_aligned, (gt_bin.shape[1], gt_bin.shape[0]))  # resize aligned map

    # =========================
    # IoU（已修正）
    # =========================
    intersection = np.logical_and(gt_bin, slam_bin) & mask
    union = np.logical_or(gt_bin, slam_bin) & mask

    iou = np.sum(intersection) / np.sum(union)

    # =========================
    # SSIM
    # =========================
    ssim_score, _ = ssim(gt_img, slam_aligned, full=True)

    # =========================
    # output
    # =========================
    print("\n===== RESULT =====")
    print("IoU :", iou)
    print("SSIM:", ssim_score)

    # save aligned result
    cv2.imwrite(BASE_PATH + "/aligned_slam_phase.pgm", slam_aligned)

    print("Saved: aligned_slam_phase.pgm")