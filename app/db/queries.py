"""
Database queries for appointments and conversations
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from app.db.connection import get_connection

logger = logging.getLogger(__name__)


async def get_appointments_between_dates(
    start_date: datetime,
    end_date: datetime
) -> List[Dict]:
    """
    Get all appointments between two dates
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        List of appointments
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        customer_name,
                        customer_email,
                        service_name,
                        starts_at,
                        status
                    FROM booknetic_appointments
                    WHERE starts_at >= %s
                      AND starts_at <= %s
                      AND status NOT IN ('cancelled', 'rejected')
                    ORDER BY starts_at
                """, (start_date, end_date))
                
                results = cur.fetchall()
                
                appointments = []
                for row in results:
                    appointments.append({
                        "id": row[0],
                        "customer_name": row[1],
                        "customer_email": row[2],
                        "service_name": row[3],
                        "starts_at": row[4].isoformat() if row[4] else None,
                        "status": row[5]
                    })
                
                return appointments
    
    except Exception as e:
        logger.error(f"Error querying appointments: {e}")
        return []


async def save_conversation(
    phone_number: str,
    customer_name: str,
    message_text: str,
    response_text: str,
    message_type: str = "text",
    message_id: str = None,
    direction: str = "incoming"
) -> None:
    """
    Save conversation to database for analytics
    
    Args:
        phone_number: Customer phone
        customer_name: Customer name
        message_text: User's message
        response_text: Bot's response
        message_type: Type of message
        message_id: WhatsApp message ID (to avoid duplicates)
        direction: 'incoming' or 'outgoing'
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Check if message already exists (by message_id if available)
                if message_id:
                    cur.execute("""
                        SELECT id FROM whatsapp_conversations 
                        WHERE message_id = %s
                    """, (message_id,))
                    if cur.fetchone():
                        logger.info(f"Conversation with message_id {message_id} already exists, skipping")
                        return
                
                cur.execute("""
                    INSERT INTO whatsapp_conversations 
                    (phone_number, customer_name, message_text, response_text, message_type, message_id, direction, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (phone_number, customer_name, message_text, response_text, message_type, message_id, direction))
            conn.commit()
            logger.info(f"Conversation saved for {phone_number}")
    
    except Exception as e:
        logger.warning(f"Could not save conversation: {e}")
        # Don't fail if we can't save - this is not critical


async def get_recent_conversations(limit: int = 50) -> List[Dict]:
    """
    Get recent conversations from database
    
    Args:
        limit: Maximum number of conversations to return
    
    Returns:
        List of conversations
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        phone_number,
                        customer_name,
                        message_text,
                        response_text,
                        message_type,
                        created_at
                    FROM whatsapp_conversations
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
                
                conversations = []
                for row in results:
                    conversations.append({
                        "id": row[0],
                        "phone_number": row[1],
                        "customer_name": row[2],
                        "message_text": row[3],
                        "response_text": row[4],
                        "message_type": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })
                
                return conversations
    
    except Exception as e:
        logger.error(f"Error querying conversations: {e}")
        return []



