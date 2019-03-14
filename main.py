import VK_thread
import TG_thread
import time
vk = VK_thread.VkThread()
#tel = TG_thread.TelegramThread()


vk.start()
time.sleep(10)
#tel.start()