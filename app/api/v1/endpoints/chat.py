"""Chat and RAG endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.schemas.chat import ChatMessageRequest
from app.models.chat import ChatMessage

router = APIRouter()

@router.post("/session")
async def create_chat_session(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new chat session"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    session = rag_service.get_or_create_session(db, user.id, user_type)
    return {"session_id": session.id, "started_at": session.started_at}

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send chat message and get AI response"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    try:
        # Get or create session
        session = rag_service.get_or_create_session(
            db, user.id, user_type, request.session_id
        )
        
        # Save user message
        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.flush()
        
        # Retrieve context
        context = rag_service.retrieve_context(
            request.message, user.id, user_type, db
        )
        
        # Get persistent memory
        persistent_memory = rag_service.get_persistent_memory(db, user.id, user_type)
        
        # Generate response
        response = gemini_service.generate_chat_response(
            request.message,
            context,
            session.ephemeral_memory,
            persistent_memory
        )
        
        # Save assistant response
        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response["response"],
            intent=response.get("intent"),
            provenance={
                "transaction_ids": response.get("provenance", []),
                "confidence": response.get("confidence")
            },
            retrieved_docs=context
        )
        db.add(assistant_message)
        
        # Update session memory
        session.ephemeral_memory["last_query"] = request.message
        session.ephemeral_memory["last_intent"] = response.get("intent")
        
        db.commit()
        
        return {
            "session_id": session.id,
            "response": response["response"],
            "intent": response.get("intent"),
            "confidence": response.get("confidence"),
            "provenance": {"transaction_ids": response.get("provenance", [])},
            "retrieved_docs": context
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/session/{session_id}/history")
async def get_chat_history(
    session_id: int,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history for a session"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    # Verify session belongs to user
    from app.models.chat import ChatSession
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check ownership
    if user_type == "consumer" and session.user_consumer_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    elif user_type == "business" and session.user_business_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp.asc()).limit(limit).all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "intent": msg.intent,
                "provenance": msg.provenance
            }
            for msg in messages
        ]
    }

@router.post("/exact-lookup")
async def exact_lookup(
    merchant_name: str = None,
    amount: float = None,
    date: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exact transaction lookup using database query"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    try:
        # Parse date if provided
        parsed_date = None
        if date:
            from dateparser import parse
            parsed_date = parse(date)
        
        # Perform exact lookup
        results = rag_service.exact_lookup(
            db=db,
            user_id=user.id,
            user_type=user_type,
            merchant_name=merchant_name,
            amount=amount,
            date=parsed_date
        )
        
        return {
            "results": results,
            "count": len(results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup error: {str(e)}")

@router.post("/memory")
async def store_memory(
    key: str,
    value: str,
    visibility: str = "persistent",
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store persistent user memory"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    try:
        from app.models.chat import ChatMemory
        
        # Check if memory exists
        if user_type == "consumer":
            memory = db.query(ChatMemory).filter(
                ChatMemory.user_consumer_id == user.id,
                ChatMemory.key == key
            ).first()
        else:
            memory = db.query(ChatMemory).filter(
                ChatMemory.user_business_id == user.id,
                ChatMemory.key == key
            ).first()
        
        if memory:
            # Update existing
            memory.value = value
            memory.updated_at = datetime.utcnow()
        else:
            # Create new
            memory = ChatMemory(
                user_consumer_id=user.id if user_type == "consumer" else None,
                user_business_id=user.id if user_type == "business" else None,
                key=key,
                value=value,
                visibility=visibility
            )
            db.add(memory)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Memory '{key}' saved successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Memory storage error: {str(e)}")
