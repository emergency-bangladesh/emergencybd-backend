import io
from typing import IO
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from PIL import Image

from ...core.config import config
from ...database.models.issue import LostAndFoundIssue
from ...database.models.volunteer import Volunteer
from ..dependencies import DatabaseSession
from ..global_schema import ApiResponse
from .schema import FileUploadData

router = APIRouter(prefix="/file-upload", tags=["File Upload"])
nid_fernet = Fernet(config.nid_encryption_key)


def _process_img(
    image_file: IO[bytes],
    max_allowed_dimension: int = 1000,
) -> io.BytesIO:
    try:
        img = Image.open(image_file)
        original_width, original_height = img.size

        # Only resize if the longest side > 1000px
        if max(original_width, original_height) > max_allowed_dimension:
            if original_width > original_height:
                new_width = max_allowed_dimension
                new_height = int(original_height * (new_width / original_width))
            else:
                new_height = max_allowed_dimension
                new_width = int(original_width * (new_height / original_height))

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # type: ignore

        img_buffer = io.BytesIO()
        img.save(img_buffer, "WEBP", quality=75)  # Save with high quality
        return img_buffer

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image data: {e}"
        )
    finally:
        image_file.close()


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
    nid_1_img_data = _process_img(nid_first_img.file, 1000)
    encrypted_nid_1_img_data = nid_fernet.encrypt(nid_1_img_data.getvalue())

    nid_second_img_path = config.construct_nid_second_image_path(volunteer_uuid)
    nid_2_img_data = _process_img(nid_second_img.file, 1000)
    nid_2_encrypted_img_data = nid_fernet.encrypt(nid_2_img_data.getvalue())

    with open(nid_first_img_path, "wb") as nid_1_img_file:
        nid_1_img_file.write(encrypted_nid_1_img_data)

    with open(nid_second_img_path, "wb") as nid_2_img_file:
        nid_2_img_file.write(nid_2_encrypted_img_data)

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
    profile_img_data = _process_img(profile_pic.file, 376)

    with open(profile_pic_path, "wb") as profile_pic_file:
        profile_pic_file.write(profile_img_data.getvalue())

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
        img_data = _process_img(image.file, 1000)
        with open(image_path, "wb") as img_file:
            img_file.write(img_data.getvalue())

    return ApiResponse(
        message="Lost and Found issue images uploaded successfully",
        data=FileUploadData(uploaded=True),
    )
