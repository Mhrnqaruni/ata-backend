# /app/routers/classes_router.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from typing import List
import json

from ..models import class_model, student_model
from ..services import class_service, database_service

router = APIRouter()

# --- CLASS COLLECTION ENDPOINTS (/api/classes) ---

@router.get("", response_model=List[class_model.ClassSummary], summary="Get All Classes with Student Counts")
def get_all_classes(db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    # --- [THE FIX IS HERE] ---
    # We now pass the hardcoded user_id from the router down to the service.
    user_id = "user_v1_demo"
    return class_service.get_all_classes_with_summary(user_id=user_id, db=db)
    # --- [END OF FIX] ---

@router.post("", response_model=class_model.Class, status_code=status.HTTP_201_CREATED, summary="Create a New Class Manually")
def create_new_class(class_create: class_model.ClassCreate, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    return class_service.create_class(class_data=class_create, db=db)

@router.post("/upload", response_model=class_model.ClassUploadResponse, status_code=status.HTTP_202_ACCEPTED, summary="Create a Class via File Upload")
async def create_class_with_upload(db: database_service.DatabaseService = Depends(database_service.get_db_service), name: str = Form(...), file: UploadFile = File(...)):
    try:
        result = await class_service.create_class_from_upload(name=name, file=file, db=db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {e}")

# --- INDIVIDUAL CLASS RESOURCE ENDPOINTS (/api/classes/{class_id}) ---

@router.get("/{class_id}", response_model=class_model.ClassDetails, summary="Get a Single Class with Full Details")
def get_class_by_id(class_id: str, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    class_details = class_service.get_class_details_by_id(class_id=class_id, db=db)
    if class_details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class with ID {class_id} not found")
    return class_details

@router.put("/{class_id}", response_model=class_model.Class, summary="Update a Class")
def update_class_details(class_id: str, class_update: class_model.ClassCreate, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    try:
        updated_class = class_service.update_class(class_id=class_id, class_update=class_update, db=db)
        if updated_class is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class with ID {class_id} not found")
        return updated_class
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Class")
def delete_class(class_id: str, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    was_deleted = class_service.delete_class_by_id(class_id=class_id, db=db)
    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Class with ID {class_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{class_id}/export", summary="Export Class Roster as CSV", response_class=StreamingResponse)
def export_class_roster_csv(class_id: str, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    try:
        csv_string = class_service.export_roster_as_csv(class_id=class_id, db=db)
        class_details = class_service.get_class_details_by_id(class_id, db)
        class_name = class_details.get('name', 'class_roster') if class_details else 'class_roster'
        file_name = f"roster_{class_name.replace(' ', '_').lower()}.csv"
        return StreamingResponse(iter([csv_string]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={file_name}"})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# --- STUDENT SUB-RESOURCE ENDPOINTS ---

@router.post("/{class_id}/students", response_model=student_model.Student, status_code=status.HTTP_201_CREATED, summary="Add a Student to a Class")
def add_student(class_id: str, student_create: student_model.StudentCreate, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    try:
        new_student = class_service.add_student_to_class(class_id=class_id, student_data=student_create, db=db)
        return new_student
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{class_id}/students/{student_id}", response_model=student_model.Student, summary="Update a Student")
def update_student_details(class_id: str, student_id: str, student_update: student_model.StudentUpdate, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    try:
        updated_student = class_service.update_student(student_id=student_id, student_update=student_update, db=db)
        if updated_student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with ID {student_id} not found")
        return updated_student
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{class_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a Student from a Class")
def remove_student_from_class(class_id: str, student_id: str, db: database_service.DatabaseService = Depends(database_service.get_db_service)):
    was_deleted = class_service.delete_student_from_class(class_id=class_id, student_id=student_id, db=db)
    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with ID {student_id} not found in class {class_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)