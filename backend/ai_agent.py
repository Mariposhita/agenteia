import openai # type: ignore
from config import Config
import json
import re

class AIAgent:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.system_prompt = """
        Eres un asistente especializado en soporte técnico de hardware y software.
        Tu función es:
        1. Analizar problemas técnicos
        2. Proporcionar soluciones básicas
        3. Clasificar si un problema es simple o complejo
        4. Determinar si es mantenimiento preventivo o correctivo
        
        Responde en formato JSON con esta estructura:
        {
            "solucion": "descripción de la solución",
            "es_complejo": true/false,
            "tipo_mantenimiento": "preventivo/correctivo",
            "pasos": ["paso1", "paso2", "paso3"],
            "requiere_admin": true/false
        }
        
        Si el problema es complejo o requiere intervención física, marca requiere_admin como true.
        """
    
    def analizar_problema(self, descripcion, categoria):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Problema de {categoria}: {descripcion}"}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Intentar parsear JSON
            try:
                resultado = json.loads(content)
            except:
                # Si no es JSON válido, crear respuesta básica
                resultado = {
                    "solucion": content,
                    "es_complejo": True,
                    "tipo_mantenimiento": "correctivo",
                    "pasos": ["Revisar el problema manualmente"],
                    "requiere_admin": True
                }
            
            return resultado
            
        except Exception as e:
            print(f"Error en IA: {e}")
            return {
                "solucion": "Error al procesar. Se asignará a un técnico.",
                "es_complejo": True,
                "tipo_mantenimiento": "correctivo",
                "pasos": ["Contactar soporte técnico"],
                "requiere_admin": True
            }
    
    def generar_respuesta_chat(self, mensaje, historial=[]):
        try:
            messages = [{"role": "system", "content": "Eres un asistente de soporte técnico amigable."}]
            
            # Añadir historial
            for h in historial:
                messages.append({"role": "user", "content": h["usuario"]})
                messages.append({"role": "assistant", "content": h["ia"]})
            
            messages.append({"role": "user", "content": mensaje})
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Lo siento, hay un problema temporal. Error: {str(e)}"