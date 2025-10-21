import io
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from PIL import Image

from ...core.config import config
from ...database.models.issue import LostAndFoundIssue
from ...database.models.volunteer import Volunteer
from ..dependencies import DatabaseSession
from ..global_schema import ApiResponse
from .schema import FileUploadData

router = APIRouter(prefix="/file-upload", tags=["File Upload"])


def _process_and_save_image(image_file: UploadFile, output_path: str):
    try:
        img = Image.open(image_file.file)

        original_width, original_height = img.size
        max_side = max(original_width, original_height)

        # Only resize if the longest side > 1000px
        if max_side > 1000:
            if original_width > original_height:
                new_width = 1000
                new_height = int(original_height * (new_width / original_width))
            else:
                new_height = 1000
                new_width = int(original_width * (new_height / original_height))

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # type: ignore

        img_buffer = io.BytesIO()
        img.save(img_buffer, "WEBP", quality=80)  # Save with high quality

        with open(output_path, "wb") as f:
            f.write(img_buffer.getvalue())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image data: {e}"
        )
    finally:
        image_file.file.close()


@router.post("/volunteer/nid", response_model=ApiResponse[FileUploadData])
async def upload_nid_images(
    db: DatabaseSession,
    volunteer_uuid: UUID = Form(...),
    nid_first_img: UploadFile = File(...),
    nid_second_img: UploadFile = File(...),
):
    volunteer = db.get(Volunteer, volunteer_uuid)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found"
        )

    nid_first_img_path = config.construct_nid_first_image_path(volunteer_uuid)
    _process_and_save_image(nid_first_img, str(nid_first_img_path))

    nid_second_img_path = config.construct_nid_second_image_path(volunteer_uuid)
    _process_and_save_image(nid_second_img, str(nid_second_img_path))

    return ApiResponse(
        message="NID images uploaded successfully", data=FileUploadData(uploaded=True)
    )


@router.post("/volunteer/profile-pic", response_model=ApiResponse[FileUploadData])
async def upload_profile_pic(
    db: DatabaseSession,
    volunteer_uuid: UUID = Form(...),
    profile_pic: UploadFile = File(...),
):
    volunteer = db.get(Volunteer, volunteer_uuid)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found"
        )

    profile_pic_path = config.construct_profile_pic_path(volunteer_uuid)
    _process_and_save_image(profile_pic, str(profile_pic_path))

    return ApiResponse(
        message="Profile picture uploaded successfully",
        data=FileUploadData(uploaded=True),
    )


@router.post("/issue/lost-and-found", response_model=ApiResponse[FileUploadData])
async def upload_lost_and_found_images(
    db: DatabaseSession,
    issue_uuid: UUID = Form(...),
    images: list[UploadFile] = File(...),
):
    if not 1 <= len(images) <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must upload between 1 and 3 images",
        )

    issue = db.get(LostAndFoundIssue, issue_uuid)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lost and Found Issue not found",
        )

    for i, image in enumerate(images):
        image_path = config.construct_lost_and_found_image_path(issue_uuid, i + 1)
        _process_and_save_image(image, str(image_path))

    return ApiResponse(
        message="Lost and Found issue images uploaded successfully",
        data=FileUploadData(uploaded=True),
    )
