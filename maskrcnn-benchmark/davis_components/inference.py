import cv2
import torch
from torchvision import transforms as T


def select_top_predictions(predictions, confidence_threshold=0.7):
    """
    Select only predictions which have a `score` > self.confidence_threshold,
    and returns the predictions in descending order of score

    Arguments:
        predictions (BoxList): the result of the computation by the model.
            It should contain the field `scores`.

    Returns:
        prediction (BoxList): the detected objects. Additional information
            of the detection properties can be found in the fields of
            the BoxList via `prediction.fields()`
    """
    scores = predictions.get_field("scores")
    keep = torch.nonzero(scores >  confidence_threshold).squeeze(1)
    predictions = predictions[keep]
    scores = predictions.get_field("scores")
    _, idx = scores.sort(0, descending=True)
    return predictions[idx]


def overlay_boxes(image, predictions):
    """
    Adds the predicted boxes on top of the image

    Arguments:
        image (np.ndarray): an image as returned by OpenCV
        predictions (BoxList): the result of the computation by the model.
            It should contain the field `labels`.
    """
    labels = predictions.get_field("labels")
    boxes = predictions.bbox

    colors = compute_colors_for_labels(labels).tolist()

    for box, color in zip(boxes, colors):
        box = box.to(torch.int64)
        top_left, bottom_right = box[:2].tolist(), box[2:].tolist()
        image = cv2.rectangle(
            image, tuple(top_left), tuple(bottom_right), tuple(color), 1
        )

    return image


def compute_colors_for_labels(labels):
    """
    Simple function that adds fixed colors depending on the class
    """
    palette = torch.tensor([2 ** 25 - 1, 2 ** 15 - 1, 2 ** 21 - 1])
    colors = labels[:, None] * palette
    colors = (colors % 255).numpy().astype("uint8")
    return colors


def vote_pixelOfMask_for_annotation(masks, predictions):
    '''
    Each prediction(box) possiblely overlaps with others,  but there is only one label
    to represent each instance's pixels in the final annotation.
    Thus, we need to decide which instance each pixel belongs to. For each pixel,
    we define a pixel score for each instance, and choose the instance with
    the maximum pixel score as its pixel's label

    For each pixel:
    Pixel Score = foreground probability in the mask * its mask's class probability
    (In DAVIS, there is only 2 categories)

    Arguments:
        predictions (BoxList): the result of the computation by the model.
            It should contain the field `scores`.'label'
        masks (torch.tensor):  a set of masks (prediction.get_field("mask"))have been projected
            in an image on the locations specified by the bounding boxes

    Returns:
        prediction (BoxList): the detected objects. Additional information
            of the detection properties can be found in the fields of
            the BoxList via `prediction.fields()`
    '''