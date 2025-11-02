"""
Availability checker - queries PostgreSQL for appointment availability
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncio
import re

from app.db.queries import get_appointments_between_dates

logger = logging.getLogger(__name__)


class AvailabilityChecker:
    """Check availability by querying appointments database"""
    
    async def check_availability(self, message: str) -> str:
        """
        Check availability based on user query
        
        Args:
            message: User's message asking about availability
        
        Returns:
            Response with availability information
        """
        try:
            # Parse date from message if possible
            today = datetime.now()
            start_date = today
            
            # Try to extract date keywords from message
            message_lower = message.lower()
            
            # Determine end date based on query
            if "mañana" in message_lower or "tomorrow" in message_lower:
                end_date = today + timedelta(days=1)
            elif "próxima semana" in message_lower or "next week" in message_lower:
                end_date = today + timedelta(days=7)
            elif "mes" in message_lower or "month" in message_lower:
                end_date = today + timedelta(days=30)
            else:
                # Default: next 7 days
                end_date = today + timedelta(days=7)
            
            # Query appointments from database
            appointments = await get_appointments_between_dates(start_date, end_date)
            
            logger.info(f"Found {len(appointments)} appointments between {start_date.date()} and {end_date.date()}")
            
            # If no appointments, return all available
            if len(appointments) == 0:
                response = """✅ **Tenemos disponibilidad!**
                
📅 Para los próximos días tenemos horarios disponibles.

👥 ¿Para cuántas personas sería la experiencia HotBoat?

⏰ **Horarios sugeridos:**
• Mañana: 10:00, 14:00, 16:00
• Después: Consúltame horarios específicos

💡 Reserva aquí:
https://hotboatchile.com/es/book-hotboat/"""
            else:
                # Format booked appointments
                booked_info = []
                for apt in appointments[:5]:  # Show max 5 appointments
                    date = datetime.fromisoformat(apt['starts_at']) if isinstance(apt['starts_at'], str) else apt['starts_at']
                    booked_info.append(f"\n• {date.strftime('%d/%m')} {date.strftime('%H:%M')} - {apt['customer_name']}")
                
                booked_text = "".join(booked_info) if booked_info else "\n• No hay reservas confirmadas"
                
                response = f"""📅 **Disponibilidad consultada**

Consulté los próximos días y tenemos algunas reservas:
{booked_text}

✅ **¡Tenemos disponibilidad!** Para horarios específicos, dime:
👥 ¿Para cuántas personas?
📅 ¿Qué día prefieres?

💡 También puedes reservar aquí:
https://hotboatchile.com/es/book-hotboat/"""
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            import traceback
            traceback.print_exc()
            return "Disculpa, tuve un problema consultando la disponibilidad. Te responderé en un momento. Gracias por tu paciencia 🙏"
    
    async def get_available_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        party_size: Optional[int] = None
    ) -> List[Dict]:
        """
        Get available time slots from database
        
        Args:
            start_date: Start date for search
            end_date: End date for search
            party_size: Number of people (optional)
        
        Returns:
            List of available slots
        """
        # TODO: Implement real database query
        # This will query the booknetic_appointments table
        # and find gaps/available times
        
        return []



