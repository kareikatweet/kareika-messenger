from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# USER MODELS
class UserCreate(BaseModel):
    username: str
    mnemonic: str
    email: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    mnemonic: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    phone: Optional[str]
    status: str
    created_at: str

class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str]
    phone: Optional[str]
    status: str

# GROUP MODELS
class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    admin_id: int
    description: Optional[str]
    created_at: str

class GroupMemberResponse(BaseModel):
    id: int
    username: str
    status: str
    role: str

class GroupDetailsResponse(BaseModel):
    id: int
    name: str
    admin_id: int
    description: Optional[str]
    members: List[GroupMemberResponse]
    created_at: str

# MESSAGE MODELS
class MessageCreate(BaseModel):
    text: str
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    message_type: str = "text"

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    receiver_id: Optional[int]
    group_id: Optional[int]
    text: str
    message_type: str
    timestamp: str
    is_deleted: bool

class MessageDelete(BaseModel):
    message_id: int

class MessageUpdate(BaseModel):
    text: Optional[str] = None

# MEDIA MODELS
class MediaCreate(BaseModel):
    file_name: str
    file_type: str
    file_size: int

class MediaResponse(BaseModel):
    id: int
    message_id: int
    file_name: str
    file_type: str
    file_size: int
    uploaded_at: str

class FileUpload(BaseModel):
    message_id: int
    file_name: str
    file_type: str
    file_size: int

# NOTIFICATION MODELS
class NotificationCreate(BaseModel):
    type: str
    title: str
    message: str
    data: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    data: Optional[str]
    created_at: str
    read_at: Optional[str]

class NotificationMarkRead(BaseModel):
    notification_id: int

# CALL MODELS
class CallCreate(BaseModel):
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    call_type: str = "voice"

class CallResponse(BaseModel):
    id: int
    caller_id: int
    receiver_id: Optional[int]
    group_id: Optional[int]
    status: str
    call_type: str
    started_at: str
    ended_at: Optional[str]
    duration: Optional[int]

class CallEnd(BaseModel):
    call_id: int

# AUTHENTICATION MODELS
class AuthResponse(BaseModel):
    type: str
    status: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    reason: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

# CONTACT MODELS
class ContactResponse(BaseModel):
    id: int
    username: str
    status: str
    email: Optional[str]
    phone: Optional[str]

# CHAT WINDOW MODELS
class ChatWindowRequest(BaseModel):
    user_id: int
    chat_type: str  # "direct" or "group"
    target_id: int  # receiver_id or group_id

class ChatWindowResponse(BaseModel):
    chat_type: str
    target_id: int
    target_name: str
    messages: List[MessageResponse]
    participants: Optional[List[GroupMemberResponse]]

# BATCH OPERATIONS
class BatchDeleteMessages(BaseModel):
    message_ids: List[int]

class BatchAddGroupMembers(BaseModel):
    user_ids: List[int]
    group_id: int

# SEARCH MODELS
class SearchRequest(BaseModel):
    query: str
    search_type: str  # "users", "groups", "messages"

class SearchResponse(BaseModel):
    type: str
    results: List[dict]

# STATUS MODELS
class StatusUpdate(BaseModel):
    status: str  # "online", "offline", "away", "busy"

class OnlineStatusResponse(BaseModel):
    user_id: int
    status: str
    timestamp: str

# ERROR RESPONSE
class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    code: Optional[str] = None

# SUCCESS RESPONSE
class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
