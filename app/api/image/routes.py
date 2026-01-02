import os
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, Response

from ...core.config import config
from ..dependencies import CurrentAdmin
from ..global_schema import ApiResponse

router = APIRouter(prefix="/image", tags=["Image Delivery"])
nid_fernet = Fernet(config.nid_encryption_key)


@router.get("/volunteer/{uuid}/profile-pic")
async def get_profile_pic(uuid: UUID):
    file_path = config.construct_profile_pic_path(uuid)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    return FileResponse(file_path, media_type="image/webp")


@router.get("/volunteer/{uuid}/nid-1")
async def get_nid_1(uuid: UUID, _: CurrentAdmin):
    file_path = config.construct_nid_first_image_path(uuid)
    if not os.path.exists(file_path):
        if not os.path.exists(str(file_path).replace(".encrypted", ".webp")):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )
        else:
            # encrypted if unencrypted
            with open(str(file_path).replace(".encrypted", ".webp"), "rb") as f:
                encrypted_image_data = nid_fernet.encrypt(f.read())
                with open(file_path, "wb") as f:
                    f.write(encrypted_image_data)

    with open(file_path, "rb") as f:
        decrypted_img_data = nid_fernet.decrypt(f.read())
    return Response(content=decrypted_img_data, media_type="image/webp")


@router.get("/volunteer/{uuid}/nid-2")
async def get_nid_2(uuid: UUID, _: CurrentAdmin):
    file_path = config.construct_nid_second_image_path(uuid)
    if not os.path.exists(file_path):
        if not os.path.exists(str(file_path).replace(".encrypted", ".webp")):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )
        else:
            # encrypted if unencrypted
            with open(str(file_path).replace(".encrypted", ".webp"), "rb") as f:
                encrypted_image_data = nid_fernet.encrypt(f.read())
                with open(file_path, "wb") as f:
                    f.write(encrypted_image_data)

    return FileResponse(file_path, media_type="image/webp")


@router.get("/issue/lost-and-found/{issue_uuid}/image-{image_number}")
async def get_lost_and_found_image(issue_uuid: UUID, image_number: int):
    if not 1 <= image_number <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image number must be between 1 and 3",
        )
    file_path = config.construct_lost_and_found_image_path(issue_uuid, image_number)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    return FileResponse(file_path, media_type="image/webp")


@router.get(
    "/issue/lost-and-found/{issue_uuid}/images",
    response_model=ApiResponse[list[str]],
)
async def get_lost_and_found_images_list(issue_uuid: UUID):
    image_urls: list[str] = []
    found_images_count = 0
    for i in range(1, 4):  # Check for images 1 to 3
        file_path = config.construct_lost_and_found_image_path(issue_uuid, i)
        if os.path.exists(file_path):
            image_urls.append(f"/image/issue/lost-and-found/{issue_uuid}/image-{i}")
            found_images_count += 1

    if not image_urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No images found for this issue",
        )

    return ApiResponse(
        message=f"Fetched successfully, found {found_images_count} images",
        data=image_urls,
    )
