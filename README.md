# PetDayCare
Pet Day Care Website using Flask and SQLite

# Requirements:
1. Flask
2. WTForms
3. passlib
4. functools

# Instructions:
1. To access admin account username is "admin" and password is "admin123"
2. While booking an appointment, please ensure:
         1. date entered is in format 'DD/MM/YYYY"
         2. time entered is in 24 hour format "HH:MM"
         
# Assumptions:
1. Slots are of 1 hour and each slot time starts from XX:00 and ends at XX:59
2. For every slot atmost 5 bookings can be made.
3. Price for each slot is fixed.
4. All payments has to be made offline.
5. Admin has to update pending amount of each user after recieving payment.
