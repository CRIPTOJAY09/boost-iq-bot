import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def verify_transaction(tx_hash: str, wallet_address: str, contract_address: str, api_key: str) -> tuple[bool, float]:
    """
    Verificar transacción en BSCScan
    
    Args:
        tx_hash: Hash de la transacción
        wallet_address: Dirección de la billetera de destino
        contract_address: Dirección del contrato USDT
        api_key: API key de BSCScan
    
    Returns:
        tuple: (es_válida, cantidad)
    """
    try:
        # URL de la API de BSCScan
        url = "https://api.bscscan.com/api"
        
        # Parámetros para obtener detalles de la transacción
        params = {
            "module": "proxy",
            "action": "eth_getTransactionByHash",
            "txhash": tx_hash,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("result"):
            logger.warning(f"Transacción no encontrada: {tx_hash}")
            return False, 0.0
        
        tx_data = data["result"]
        
        # Verificar que la transacción sea al contrato USDT
        if tx_data.get("to", "").lower() != contract_address.lower():
            logger.warning(f"Transacción no es al contrato USDT: {tx_hash}")
            return False, 0.0
        
        # Obtener el recibo de la transacción para verificar el status
        receipt_params = {
            "module": "proxy",
            "action": "eth_getTransactionReceipt",
            "txhash": tx_hash,
            "apikey": api_key
        }
        
        receipt_response = requests.get(url, params=receipt_params, timeout=10)
        receipt_response.raise_for_status()
        
        receipt_data = receipt_response.json()
        
        if not receipt_data.get("result"):
            logger.warning(f"Recibo de transacción no encontrado: {tx_hash}")
            return False, 0.0
        
        receipt = receipt_data["result"]
        
        # Verificar que la transacción fue exitosa
        if receipt.get("status") != "0x1":
            logger.warning(f"Transacción falló: {tx_hash}")
            return False, 0.0
        
        # Verificar timestamp (no más de 24 horas)
        block_number = int(receipt.get("blockNumber", "0"), 16)
        if not is_recent_transaction(block_number, api_key):
            logger.warning(f"Transacción muy antigua: {tx_hash}")
            return False, 0.0
        
        # Analizar logs para encontrar la transferencia
        logs = receipt.get("logs", [])
        amount = parse_transfer_amount(logs, wallet_address)
        
        if amount > 0:
            logger.info(f"Transacción verificada: {tx_hash}, cantidad: {amount}")
            return True, amount
        else:
            logger.warning(f"No se encontró transferencia válida: {tx_hash}")
            return False, 0.0
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red verificando transacción: {e}")
        return False, 0.0
    except Exception as e:
        logger.error(f"Error verificando transacción: {e}")
        return False, 0.0

def is_recent_transaction(block_number: int, api_key: str) -> bool:
    """
    Verificar si la transacción es reciente (menos de 24 horas)
    """
    try:
        url = "https://api.bscscan.com/api"
        params = {
            "module": "proxy",
            "action": "eth_getBlockByNumber",
            "tag": hex(block_number),
            "boolean": "true",
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("result"):
            return False
        
        block = data["result"]
        timestamp = int(block.get("timestamp", "0"), 16)
        block_time = datetime.fromtimestamp(timestamp)
        
        # Verificar que no sea más de 24 horas
        time_diff = datetime.now() - block_time
        return time_diff <= timedelta(hours=24)
        
    except Exception as e:
        logger.error(f"Error verificando timestamp del bloque: {e}")
        return False

def parse_transfer_amount(logs: list, wallet_address: str) -> float:
    """
    Analizar logs para encontrar la cantidad transferida
    """
    try:
        # Topic para Transfer event: keccak256("Transfer(address,address,uint256)")
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        wallet_address_padded = "0x" + wallet_address[2:].lower().zfill(64)
        
        for log in logs:
            topics = log.get("topics", [])
            
            # Verificar si es un evento Transfer
            if len(topics) >= 3 and topics[0] == transfer_topic:
                # topics[1] = from address
                # topics[2] = to address  
                to_address = topics[2]
                
                # Verificar si es transferencia a nuestra wallet
                if to_address.lower() == wallet_address_padded.lower():
                    # La cantidad está en el data field
                    data = log.get("data", "0x")
                    if len(data) >= 66:  # 0x + 64 chars
                        amount_hex = data[2:]  # Remover 0x
                        amount_wei = int(amount_hex, 16)
                        # USDT tiene 18 decimales
                        amount_usdt = amount_wei / (10 ** 18)
                        return amount_usdt
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error analizando logs: {e}")
        return 0.0
